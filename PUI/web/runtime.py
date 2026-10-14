"""One worker's serial PUI runtime and live binding/event registrations."""
import asyncio
from copy import deepcopy
import threading

from ..node import PUIEvent
from ..state import AttrBinding, ListBinding, DictBinding
from ..dom import recur_delete
from . import widgets
from .protocol import ProtocolError, validate_data
from .messages import validate_client_body
from .render import same

EVENTS = {'click': '_onClicked', 'input': '_onInput'}


class Runtime:
    def __init__(self, loop):
        self.loop = loop
        self.changed = asyncio.Event()
        self._lock = threading.Lock()
        self._dirty = set()
        self._counter = 0
        self.slots = {}
        self.nodes = {}
        self.edits = {}
        self.quit_requested = False
        self.app = None
        widgets._current_runtime = self

    def identifier(self, prefix):
        self._counter += 1
        return prefix + str(self._counter)

    def wake(self):
        self.loop.call_soon_threadsafe(self.changed.set)

    def queue_view(self, view):
        with self._lock:
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
            raise NotImplementedError('Web list/dict bindings await structural revision tracking')
        else:
            owner, kind, key = binding, 'value', None
        ref = {'object_id': str(id(owner)), 'kind': kind, 'key': key}
        identity = (id(owner), kind, key)
        slot = self.slots.get(identity)
        value = deepcopy(binding.value)
        validate_data(value)
        if slot is None:
            slot = {'owner': owner, 'binding': binding, 'record': {
                'ref': ref, 'token': self.identifier('s'), 'value_rev': 1, 'value': value}}
            self.slots[identity] = slot
        else:
            slot['binding'] = binding
            if not same(value, slot['record']['value']):
                slot['record']['value'] = value
                slot['record']['value_rev'] += 1
        used.add(identity)
        previous = element.attachments.get(role)
        if previous is None or previous['slot_token'] != slot['record']['token']:
            previous = {'ref': ref, 'slot_token': slot['record']['token'],
                        'token': self.identifier('a'), 'writable': True}
            element.attachments[role] = previous
        return deepcopy(previous)

    def snapshot(self):
        used, nodes, active_edits = set(), {}, set()
        def visit(element):
            node = element.node
            nodes[element.id] = element
            props = node.properties()
            layout = {name: getattr(node, 'layout_' + name)
                      for name in ('width', 'height', 'weight', 'padding', 'margin')
                      if getattr(node, 'layout_' + name) is not None}
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
            events = {}
            for name, attr in EVENTS.items():
                if getattr(node, attr) is not None:
                    events[name] = element.events.get(name) or self.identifier('e')
                    if name == 'input':
                        active_edits.add(events[name])
            element.events = events
            bindings = {}
            if isinstance(node, widgets.TextField):
                for role in ('model', 'edit_model'):
                    binding = getattr(node, role)
                    if binding is not None:
                        bindings[role] = self._binding(element, role, binding, used)
                        active_edits.add(bindings[role]['token'])
            element.attachments = bindings
            return {'id': element.id, 'type': node.wire_type, 'props': props,
                    'layout': layout, 'style': style, 'bindings': bindings,
                    'events': events, 'children': [visit(child) for child in element.children]}
        roots = [visit(child) for child in self.app.ui.children]
        self.nodes = nodes
        self.slots = {identity: slot for identity, slot in self.slots.items() if identity in used}
        self.edits = {key: value for key, value in self.edits.items() if key[0] in active_edits}
        return {'roots': roots, 'bindings': [deepcopy(slot['record']) for slot in self.slots.values()],
                'canvases': []}

    def action(self, kind, body, *, render_rev=None):
        try:
            validate_client_body(kind, body)
        except ProtocolError as error:
            return 'invalid', error.code
        if render_rev is not None and body['observed_render_rev'] > render_rev:
            return 'invalid', 'REVISION_MISMATCH'
        element = self.nodes.get(body['node_id'])
        if element is None or element.node.destroyed:
            return 'stale', 'STALE_TARGET'
        node = element.node
        if getattr(node, 'enabled', True) is False:
            return 'stale', 'STALE_TARGET'
        if kind == 'event':
            event = body['event']
            if event not in EVENTS or element.events.get(event) != body['token']:
                return 'stale', 'STALE_TARGET'
            data = body['data']
            if event == 'input':
                if not isinstance(node, widgets.TextField):
                    return 'invalid', 'INVALID_VALUE'
                identity = (body['token'], 'input')
                if data['edit_seq'] <= self.edits.get(identity, 0):
                    return 'stale', 'STALE_TARGET'
                self.edits[identity] = data['edit_seq']
            e = PUIEvent()
            e.__dict__.update(data)
            getattr(node, '_clicked' if event == 'click' else '_input')(e)
            return 'processed', None
        if not isinstance(node, widgets.TextField):
            return 'invalid', 'INVALID_VALUE'
        role, phase = body['role'], body['phase']
        attachment = element.attachments.get(role)
        if (attachment is None or not attachment['writable'] or
                attachment['token'] != body['attachment_token'] or
                attachment['slot_token'] != body['slot_token'] or not same(attachment['ref'], body['ref'])):
            return 'stale', 'STALE_TARGET'
        ref = attachment['ref']
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

    def close(self):
        if self.app is not None:
            for child in list(self.app.children):
                recur_delete(self.app, child, True)
            self.app.destroy(True)
        self.nodes.clear()
        self.slots.clear()
        widgets._current_runtime = None
