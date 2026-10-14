"""Server-side record diffs and a single-outstanding-render stream.

These records are independent of PUI declarations and browser DOM objects. The
worker supplies stable node/token IDs; this module never derives identity from
labels or callback object addresses.
"""
from copy import deepcopy

from .protocol import ProtocolError, SAFE_INTEGER, validate_data


MAP_FIELDS = ('props', 'layout', 'style', 'bindings', 'events')
NODE_FIELDS = frozenset(('id', 'type', 'children') + MAP_FIELDS)


def same(left, right):
    """Wire equality must not confuse False/0 or True/1."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return (left.keys() == right.keys() and
                all(same(value, right[key]) for key, value in left.items()))
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def _fail(message):
    raise ProtocolError('INVALID_VALUE', message)


def _identifier(value):
    if type(value) is not str or not value:
        _fail('Expected nonempty record ID')


def _index(state):
    """Validate structural records, not component-specific property schemas."""
    validate_data(state)
    if type(state) is not dict or set(state) != {'roots', 'bindings', 'canvases'}:
        _fail('Invalid render state fields')
    if any(type(state[key]) is not list for key in state):
        _fail('Render state collections must be lists')
    nodes, parents, children = {}, {}, {None: []}

    def visit(node, parent):
        if type(node) is not dict or set(node) != NODE_FIELDS:
            _fail('Invalid node fields')
        key = node['id']
        _identifier(key)
        _identifier(node['type'])
        if key in nodes:
            _fail('Duplicate node ID')
        if type(node['children']) is not list:
            _fail('Invalid node children')
        if any(type(node[field]) is not dict for field in MAP_FIELDS):
            _fail('Invalid node map field')
        nodes[key], parents[key], children[key] = node, parent, []
        children[parent].append(key)
        for child in node['children']:
            visit(child, key)

    for root in state['roots']:
        visit(root, None)
    if len(children[None]) > 1:
        _fail('Only one application root is supported')
    slots = {}
    for slot in state['bindings']:
        if type(slot) is not dict or set(slot) != {'ref', 'token', 'value_rev', 'value'}:
            _fail('Invalid binding slot')
        token = slot['token']
        _identifier(token)
        if token in slots or type(slot['value_rev']) is not int or slot['value_rev'] <= 0:
            _fail('Duplicate slot or invalid value revision')
        ref = slot['ref']
        if (type(ref) is not dict or set(ref) != {'object_id', 'kind', 'key'} or
                type(ref['object_id']) is not str or not ref['object_id'].isascii() or
                not ref['object_id'].isdecimal() or
                ref['kind'] not in ('attr', 'list', 'dict', 'value')):
            _fail('Invalid binding reference')
        slots[token] = slot
    used = set()
    attachment_tokens = set()
    for node in nodes.values():
        for attachment in node['bindings'].values():
            if (type(attachment) is not dict or
                    set(attachment) != {'ref', 'slot_token', 'token', 'writable'} or
                    type(attachment['writable']) is not bool):
                _fail('Invalid binding attachment')
            token = attachment['token']
            _identifier(token)
            _identifier(attachment['slot_token'])
            if token in attachment_tokens:
                _fail('Duplicate attachment token')
            attachment_tokens.add(token)
            slot = slots.get(attachment['slot_token'])
            if slot is None or not same(slot['ref'], attachment['ref']):
                _fail('Attachment has no matching slot')
            used.add(slot['token'])
    if used != slots.keys():
        _fail('Unreferenced binding slot')
    canvases = {}
    for frame in state['canvases']:
        if type(frame) is not dict or 'node_id' not in frame:
            _fail('Invalid Canvas record')
        key = frame['node_id']
        _identifier(key)
        if key in canvases or key not in nodes or nodes[key]['type'] != 'Canvas':
            _fail('Invalid Canvas ownership')
        canvases[key] = frame
    return nodes, parents, children, slots, canvases


class _Order:
    """Constant-time sibling moves while constructing absolute placements."""
    def __init__(self, parents, children):
        self.parent = dict(parents)
        self.before, self.after, self.first = {}, {}, {}
        self.tail = {}
        for parent, siblings in children.items():
            self.first[parent] = siblings[0] if siblings else None
            self.tail[parent] = siblings[-1] if siblings else None
            for index, key in enumerate(siblings):
                self.before[key] = siblings[index - 1] if index else None
                self.after[key] = siblings[index + 1] if index + 1 < len(siblings) else None

    def place(self, key, parent, following):
        if key in self.parent:
            old_parent = self.parent[key]
            if old_parent == parent and self.after[key] == following:
                return False
            previous, after = self.before[key], self.after[key]
            if previous is None:
                self.first[old_parent] = after
            else:
                self.after[previous] = after
            if after is not None:
                self.before[after] = previous
        # Detaching the old tail may have changed it, including cross-parent moves.
        if key in self.parent and self.tail.get(old_parent) == key:
            self.tail[old_parent] = self.before[key]
        if following is None:
            # Retain a tail to avoid scanning wide sibling lists.
            previous = self.tail.get(parent)
            self.tail[parent] = key
        else:
            previous = self.before[following]
        self.parent[key], self.before[key], self.after[key] = parent, previous, following
        if previous is None:
            self.first[parent] = key
        else:
            self.after[previous] = key
        if following is not None:
            self.before[following] = key
        return True

def diff(previous, target):
    """Return absolute operations transforming a valid baseline into its target."""
    old, parents, children, old_slots, old_canvas = _index(previous)
    new, _, new_children, slots, canvases = _index(target)
    ops = []
    for token, slot in slots.items():
        before = old_slots.get(token)
        if before is not None:
            if not same(before['ref'], slot['ref']):
                _fail('A binding token cannot change its source')
            if slot['value_rev'] < before['value_rev'] or (
                    slot['value_rev'] == before['value_rev'] and not same(slot, before)):
                _fail('Binding revisions must describe immutable values')
        if not same(before, slot):
            ops.append({'op': 'put_binding', 'slot': deepcopy(slot)})
    for key, node in new.items():
        if key not in old:
            record = {field: deepcopy(value) for field, value in node.items() if field != 'children'}
            record['children'] = []
            ops.append({'op': 'create_node', 'node': record})
            continue
        if old[key]['type'] != node['type']:
            _fail('Changing node type requires a new wire ID')
        for field in MAP_FIELDS:
            before, after = old[key][field], node[field]
            assigned = {name: deepcopy(value) for name, value in after.items()
                        if name not in before or not same(before[name], value)}
            removed = [name for name in before if name not in after]
            if assigned or removed:
                ops.append({'op': 'patch_node', 'node_id': key, 'field': field,
                            'set': assigned, 'unset': removed})
    order = _Order(parents, children)
    # Parents occur before their children. This also breaks old ancestor
    # relationships before reversing them in the target tree.
    for parent, siblings in new_children.items():
        following = None
        for key in reversed(siblings):
            if order.place(key, parent, following):
                ops.append({'op': 'place_node', 'node_id': key,
                            'parent_id': parent, 'before_id': following})
            following = key
    for key in old:
        if key not in new and (order.parent[key] is None or order.parent[key] in new):
            ops.append({'op': 'remove_node', 'node_id': key})
    for token in old_slots:
        if token not in slots:
            ops.append({'op': 'remove_binding', 'slot_token': token})
    for key, frame in canvases.items():
        if not same(old_canvas.get(key), frame):
            ops.append({'op': 'put_canvas', 'frame': deepcopy(frame)})
    for key in old_canvas:
        if key in new and key not in canvases:
            ops.append({'op': 'remove_canvas', 'node_id': key})
    return ops


class RenderStream:
    """Own immutable copies of baseline, outstanding target, and latest desire."""
    def __init__(self):
        self._baseline = None
        self._desired = None
        self._outstanding = None
        self._issued = 0
        self._baseline_rev = 0
        self._baseline_processed = 0
        self._snapshot = True
        self._blocked = False

    @property
    def issued_rev(self):
        return self._issued

    def retained_states(self):
        """States whose image registrations can still be consumed by a client."""
        states = [self._baseline]
        if self._desired is not None:
            states.append(self._desired[0])
        if self._outstanding is not None:
            states.append(self._outstanding[0])
        return [state for state in states if state is not None]

    def offer(self, state, *, processed_seq):
        _index(state)
        if type(processed_seq) is not int or not 0 <= processed_seq <= SAFE_INTEGER:
            _fail('Invalid processed input sequence')
        latest = self._desired[1] if self._desired else self._baseline_processed
        if processed_seq < latest:
            _fail('Processed input sequence cannot go backwards')
        self._desired = (deepcopy(state), processed_seq)

    def next_render(self):
        if self._outstanding is not None or self._desired is None:
            return None
        if self._blocked and not self._snapshot:
            return None
        state, processed = self._desired
        if (not self._snapshot and same(state, self._baseline) and
                processed == self._baseline_processed):
            return None
        if self._issued == SAFE_INTEGER:
            raise ProtocolError('LIMIT_EXCEEDED', 'Render revision exhausted')
        body = {'mode': 'snapshot' if self._snapshot else 'patch',
                'base_rev': None if self._snapshot else self._baseline_rev,
                'rev': self._issued + 1, 'processed_seq': processed}
        if self._snapshot:
            body.update(deepcopy(state))
        else:
            body['ops'] = diff(self._baseline, state)
        self._issued += 1
        self._outstanding = (deepcopy(state), deepcopy(body))
        self._snapshot = False
        self._blocked = False
        return body

    def retry(self):
        """Return the exact outstanding body; transport supplies a fresh seq."""
        return deepcopy(self._outstanding[1]) if self._outstanding else None

    def acknowledge(self, *, render_rev, applied_rev, status):
        if (type(render_rev) is not int or not 0 < render_rev <= self._issued or
                type(applied_rev) is not int or not 0 <= applied_rev <= self._issued or
                status not in ('applied', 'discarded') or
                (status == 'applied' and applied_rev != render_rev)):
            raise ProtocolError('REVISION_MISMATCH', 'Invalid render acknowledgement')
        if self._outstanding is None or render_rev != self._outstanding[1]['rev']:
            return False
        state, body = self._outstanding
        self._outstanding = None
        if status == 'applied':
            self._baseline, self._baseline_rev = state, render_rev
            self._baseline_processed = body['processed_seq']
        else:
            self._blocked = True
        return True

    def resync(self, *, last_applied_rev):
        if type(last_applied_rev) is not int or not 0 <= last_applied_rev <= self._issued:
            raise ProtocolError('REVISION_MISMATCH', 'Invalid recovery revision')
        if self._outstanding is not None and self._outstanding[1]['mode'] == 'snapshot':
            return
        self._snapshot = True
