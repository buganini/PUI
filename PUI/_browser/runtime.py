"""One worker's serial PUI runtime and live binding/event registrations."""
import asyncio
import math
from copy import deepcopy
from contextlib import nullcontext
import logging

from ..node import PUIEvent
from ..state import AttrBinding, ListBinding, DictBinding, Unstate
from ..dom import recur_delete
from . import widgets
from .schema import ProtocolError, SAFE_INTEGER, validate_data
from .messages import validate_client_body
from .render import same

EVENTS = {'click': '_onClicked', 'input': '_onInput', 'drop': '_onDropped', 'dragEnter': '_onDragEntered'}


class Runtime:
    def __init__(self, loop, *, images, lock=None, call_soon=None, logger=None):
        self.loop = loop
        self.changed = asyncio.Event()
        self._lock = lock if lock is not None else nullcontext()
        self._call_soon = call_soon or loop.call_soon
        self.logger = logger or logging.getLogger("PUI._browser.widgets")
        self._dirty = set()
        self.closed = False
        self._counter = 0
        self.slots = {}
        self.nodes = {}
        self.edits = {}
        self.quit_requested = False
        self.app = None
        self.uploads = None
        self.drop_results = []
        self.images = images
        widgets._current_runtime = self

    def identifier(self, prefix):
        self._counter += 1
        return prefix + str(self._counter)

    def wake(self):
        with self._lock:
            if not self.closed:
                self._call_soon(self.changed.set)

    def queue_view(self, view):
        with self._lock:
            if self.closed:
                return
            notify = not self._dirty
            self._dirty.add(view)
        if notify:
            self.wake()

    def flush(self):
        for _ in range(100):
            with self._lock:
                dirty, self._dirty = self._dirty, set()
            if not dirty:
                return
            for view in dirty:
                if not view.destroyed and not view.retired_by:
                    view.sync()
        raise RuntimeError('Repeated redraws did not settle')

    def _binding(self, element, role, binding, used):
        if isinstance(binding, AttrBinding):
            owner, kind, key = binding.state, 'attr', binding.key
        elif isinstance(binding, (ListBinding, DictBinding)):
            owner, key = binding.state, binding.key
            kind = 'list' if isinstance(binding, ListBinding) else 'dict'
            if not ((type(key) is int and abs(key) <= SAFE_INTEGER) or
                    (kind == 'dict' and type(key) is str)):
                raise ValueError('Web list/dict binding keys require safe integers or dictionary strings')
        else:
            owner, kind, key = binding, 'value', None
        ref = {'object_id': str(id(owner)), 'kind': kind, 'key': key}
        identity = (id(owner), kind, key)
        generation = owner._binding_generation(key) if kind in ('list', 'dict') else None
        slot = self.slots.get(identity)
        value = deepcopy(Unstate(binding.value))
        validate_data(value)
        if slot is None or slot['generation'] != generation:
            slot = {'owner': owner, 'binding': binding, 'generation': generation, 'record': {
                'ref': ref, 'token': self.identifier('s'), 'value_rev': 1, 'value': value}}
            self.slots[identity] = slot
        else:
            slot['binding'] = binding
            if not same(value, slot['record']['value']):
                # Retained snapshots may still reference the preceding record.
                slot['record'] = dict(slot['record'], value=value,
                                      value_rev=slot['record']['value_rev'] + 1)
        used.add(identity)
        previous = element.attachments.get(role)
        if previous is None or previous['slot_token'] != slot['record']['token']:
            previous = {'ref': ref, 'slot_token': slot['record']['token'],
                        'token': self.identifier('a'), 'writable': True}
        # snapshot() installs a new attachment map after all roles are read;
        # the previous map may still belong to a retained render revision.
        return previous

    def snapshot(self, *, copy=True):
        """Collect render records; copy=False shares published frames/bindings.

        The worker transfers the snapshot to RenderStream. Published records
        stay read-only: Canvas replaces completed frames, and binding records
        detach live model values and are replaced when those values change.
        Backend properties() results must likewise stay unchanged after return.
        """
        used, nodes, active_edits, canvases = set(), {}, set(), []
        def visit(element):
            node = element.node
            node.validate_options()
            if isinstance(node, widgets.Window) and element is not self.app.ui.children[0]:
                raise NotImplementedError('Web nested Windows are not implemented')
            nodes[element.id] = element
            props = node.properties()
            if node._onDropped is not None:
                props['drop_extensions'] = list(node._drop_extensions) if node._drop_extensions is not None else None
            if isinstance(node, widgets.Canvas):
                frame = node.frame()
                if frame is not None:
                    canvases.append(deepcopy(frame) if copy else frame)
            layout = {name: getattr(node, 'layout_' + name)
                      for name in ('width', 'height', 'weight', 'padding', 'margin')
                      if getattr(node, 'layout_' + name) is not None}
            if node._state is not None:
                layout['observe_size'] = True
            if not node._visible:
                layout['visible'] = False
            layout.update({name: getattr(node, 'grid_' + name)
                           for name in ('row', 'column', 'rowspan', 'columnspan')
                           if getattr(node, 'grid_' + name) is not None})
            if node._grid_cell is not None:
                layout.update(zip(('row', 'column', 'rowspan', 'columnspan'), node._grid_cell))
            for name in ('padding', 'margin'):
                if name in layout:
                    layout[name] = list(layout[name])
            style = {}
            for name, attr in (('color', 'color'), ('background', 'bgcolor'),
                               ('font_size_pt', 'fontsize'), ('font_weight', 'fontweight'),
                               ('font_family', 'fontfamily')):
                value = getattr(node, 'style_' + attr)
                if value is not None:
                    style[name] = widgets.color(value) if name in ('color', 'background') else value
            previous_bindings = dict(element.attachments)
            bindings = {}
            for role in node.model_roles:
                binding = getattr(node, role)
                if binding is not None:
                    attachment = self._binding(element, role, binding, used)
                    bindings[role] = deepcopy(attachment) if copy else attachment
                    if isinstance(node, (widgets.TextField, widgets.ComboBox)):
                        active_edits.add(bindings[role]['token'])
            element.attachments = bindings
            events = {}
            handlers = dict(EVENTS)
            if isinstance(node, widgets.Canvas):
                handlers.update({name: pair[0] for name, pair in node.pointer_handlers.items()})
            for name, attr in handlers.items():
                if getattr(node, attr) is not None:
                    retained = element.events.get(name)
                    if name == 'input' and bindings != previous_bindings:
                        retained = None
                    events[name] = retained or self.identifier('e')
                    if name == 'input':
                        active_edits.add(events[name])
            if node.native_event is not None:
                context = deepcopy(node.native_context())
                validate_data(context)
                retained = bindings == previous_bindings and same(context, element.native_context)
                events[node.native_event] = ((element.events.get(node.native_event) if retained else None)
                                             or self.identifier('e'))
                element.native_context = context
                if node.native_event == 'edit':
                    active_edits.add(events[node.native_event])
            element.events = events
            return {'id': element.id, 'type': node.wire_type, 'props': props,
                    'layout': layout, 'style': style, 'bindings': bindings,
                    'events': events, 'children': [visit(child) for child in element.children]}
        children = self.app.ui.children
        if len(children) > 1 or (children and not isinstance(children[0].node, widgets.Window)):
            raise NotImplementedError('Web requires one Window as its application root')
        roots = [visit(child) for child in children]
        self.nodes = nodes
        self.slots = {identity: slot for identity, slot in self.slots.items() if identity in used}
        self.edits = {key: value for key, value in self.edits.items() if key[0] in active_edits}
        return {'roots': roots, 'bindings': [deepcopy(slot['record']) if copy else slot['record']
                                           for slot in self.slots.values()],
                'canvases': canvases}

    def size_control(self, body):
        validate_client_body('container_size', body)
        element = self.nodes.get(body['node_id'])
        if element is None or element.node.destroyed:
            return False
        if element.node._state is None:
            return False
        element.node._set_size(body['width'], body['height'])
        return bool(self._dirty)

    def canvas_control(self, kind, body):
        validate_client_body(kind, body)
        element = self.nodes.get(body['node_id'])
        if element is None or element.node.destroyed or not isinstance(element.node, widgets.Canvas):
            return False
        if kind == 'measure':
            measures = [body] + [e.node.drawing.measure for key, e in self.nodes.items()
                if key != body['node_id'] and isinstance(e.node, widgets.Canvas)]
            if sum(math.ceil(m['width'] * m['dpr']) * math.ceil(m['height'] * m['dpr'])
                   for m in measures if m is not None and m['visible']) > 33554432:
                raise ProtocolError('LIMIT_EXCEEDED', 'Canvas bitmap budget exceeded')
        return (element.node.measure(body) if kind == 'measure' else element.node.acknowledge(body))

    def reset_connection(self):
        self.edits.clear()
        for element in self.nodes.values():
            if isinstance(element.node, widgets.Table):
                element.node.reset_connection()
            if isinstance(element.node, widgets.Canvas):
                element.node.reset_connection()

    def action(self, kind, body, *, render_rev=None):
        try:
            validate_client_body(kind, body)
        except ProtocolError as error:
            return 'invalid', error.code
        if kind == 'event' and body['event'] == 'drop':
            return self.drop_action(body, render_rev)
        if render_rev is not None and body['observed_render_rev'] > render_rev:
            return 'invalid', 'REVISION_MISMATCH'
        element = self.nodes.get(body['node_id'])
        if element is None or element.node.destroyed:
            return 'stale', 'STALE_TARGET'
        node = element.node
        if getattr(node, 'disabled', False) is True:
            return 'stale', 'STALE_TARGET'
        if kind == 'event':
            event = body['event']
            if isinstance(node, widgets.Canvas) and event in node.pointer_handlers:
                if element.events.get(event) != body['token']:
                    return 'stale', 'STALE_TARGET'
                if not body['data']:
                    return 'invalid', 'INVALID_VALUE'
                node.pointer(event, body['data'])
                return 'processed', None
            if event == node.native_event:
                if (element.events.get(event) != body['token'] or
                        any(not self._live_slot(a) for a in element.attachments.values())):
                    return 'stale', 'STALE_TARGET'
                if event == 'edit':
                    identity = (body['token'], 'edit')
                    if body['data']['edit_seq'] <= self.edits.get(identity, 0):
                        return 'stale', 'STALE_TARGET'
                    self.edits[identity] = body['data']['edit_seq']
                if not node.handle_native(body['data']):
                    return 'stale', 'STALE_TARGET'
                return 'processed', None
            if event not in EVENTS or element.events.get(event) != body['token']:
                return 'stale', 'STALE_TARGET'
            data = body['data']
            if event == 'input':
                if not (isinstance(node, widgets.TextField) or
                        isinstance(node, widgets.ComboBox) and node.editable):
                    return 'invalid', 'INVALID_VALUE'
                if any(not self._live_slot(a) for a in element.attachments.values()):
                    return 'stale', 'STALE_TARGET'
                identity = (body['token'], 'input')
                if data['edit_seq'] <= self.edits.get(identity, 0):
                    return 'stale', 'STALE_TARGET'
                self.edits[identity] = data['edit_seq']
            if event == 'dragEnter':
                from ..drop import DropEvent
                callback, args, kwargs = node._onDragEntered
                callback(DropEvent(x=data['x'], y=data['y']), *args, **kwargs)
                return 'processed', None
            e = PUIEvent()
            e.__dict__.update(data)
            getattr(node, '_clicked' if event == 'click' else '_input')(e)
            return 'processed', None
        role, phase = body['role'], body['phase']
        if not (isinstance(node, widgets.TextField) or
                isinstance(node, widgets.ComboBox) and node.editable and
                (role, phase) == ('edit_model', 'input')):
            return 'invalid', 'INVALID_VALUE'
        attachment = element.attachments.get(role)
        if (attachment is None or not attachment['writable'] or
                attachment['token'] != body['attachment_token'] or
                attachment['slot_token'] != body['slot_token'] or not same(attachment['ref'], body['ref'])):
            return 'stale', 'STALE_TARGET'
        ref = attachment['ref']
        if not self._live_slot(attachment):
            return 'stale', 'STALE_TARGET'
        record = self.slots[(int(ref['object_id']), ref['kind'], ref['key'])]['record']
        if body['observed_value_rev'] > record['value_rev']:
            return 'invalid', 'REVISION_MISMATCH'
        identity = (attachment['token'], phase)
        if body['edit_seq'] <= self.edits.get(identity, 0):
            return 'stale', 'STALE_TARGET'
        self.edits[identity] = body['edit_seq']
        getattr(node, role).value = body['value']
        if phase == 'commit' and node.edit_model is not None:
            node.edit_model.value = body['value']
        e = PUIEvent()
        e.value = body['value']
        (node._change if phase == 'commit' else node._input)(e)
        return 'processed', None

    def drop_action(self, body, render_rev=None):
        from ..drop import DropEvent, dispatch
        data = body['data']
        key = data['upload_id']
        owned = False
        event = DropEvent(text=data['text'], urls=data['urls'], x=data['x'], y=data['y'])
        try:
            if key is not None:
                if self.uploads is None:
                    raise ValueError('Uploads are unavailable')
                event.files = tuple(self.uploads.take(key))
                owned = True
            element = self.nodes.get(body['node_id'])
            if (element is None or element.node.destroyed or
                    element.events.get('drop') != body['token'] or
                    (render_rev is not None and body['observed_render_rev'] > render_rev)):
                event.reject('Drop target is no longer available')
            else:
                dispatch(element.node, event)
        except FileNotFoundError:
            event.reject('Upload is no longer available')
        except Exception:
            self.logger.exception('Drop failed')
            event.reject('Drop failed or upload is no longer available')
        finally:
            if owned and not event.accepted:
                self.uploads.discard(key)
        self.drop_results.append({'accepted': event.accepted, 'reason': event.reason})
        return 'processed', None

    def drop_targets(self):
        return {key: {'token': element.events['drop'],
                      'extensions': element.node._drop_extensions}
                for key, element in self.nodes.items() if 'drop' in element.events
                and not element.node.destroyed and not getattr(element.node, 'disabled', False)}

    def _live_slot(self, attachment):
        ref = attachment['ref']
        slot = self.slots.get((int(ref['object_id']), ref['kind'], ref['key']))
        return slot is not None and slot['record']['token'] == attachment['slot_token'] and (
            ref['kind'] not in ('list', 'dict') or
            slot['owner']._binding_generation(ref['key']) == slot['generation'])

    def close(self):
        if self.uploads is not None:
            self.uploads.close()
        with self._lock:
            if self.closed:
                return
            self.closed = True
            self._dirty.clear()
        if self.app is not None:
            for child in list(self.app.children):
                recur_delete(self.app, child, True)
            self.app.destroy(True)
            self.app.destroyed = True
            self.app = None
        self.nodes.clear()
        self.slots.clear()
        self.edits.clear()
        self.changed.clear()
        self.images.close()
        if widgets._current_runtime is self:
            widgets._current_runtime = None
