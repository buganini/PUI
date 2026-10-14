"""Record diff equivalence and ACK/recovery invariants without a browser mock."""
from copy import deepcopy
import random
import unittest

from PUI.web.protocol import ProtocolError
from PUI.web.render import RenderStream, diff, same


def node(key, *children, kind='VBox', **props):
    return {'id': key, 'type': kind, 'props': props, 'layout': {}, 'style': {},
            'bindings': {}, 'events': {}, 'children': list(children)}


def state(*children):
    return {'roots': [node('window', *children, kind='Window')], 'bindings': [], 'canvases': []}


def apply(base, operations):
    """Independent, deliberately simple reference interpreter for the wire ops."""
    records, parents, lists = {}, {}, {None: []}
    slots = {x['token']: deepcopy(x) for x in base['bindings']}
    canvases = {x['node_id']: deepcopy(x) for x in base['canvases']}

    def add(record, parent):
        key = record['id']
        records[key] = {k: deepcopy(v) for k, v in record.items() if k != 'children'}
        parents[key] = parent
        lists.setdefault(parent, []).append(key)
        lists[key] = []
        for child in record['children']:
            add(child, key)

    for root in base['roots']:
        add(root, None)

    def remove(key):
        for child in list(lists[key]):
            remove(child)
        lists[parents[key]].remove(key)
        del records[key], parents[key], lists[key]
        canvases.pop(key, None)

    for operation in operations:
        op = operation['op']
        key = operation.get('node_id')
        if op == 'create_node':
            record = operation['node']
            assert record['id'] not in records and record['children'] == []
            records[record['id']] = deepcopy(record)
            lists[record['id']] = []
        elif op == 'place_node':
            parent, before = operation['parent_id'], operation['before_id']
            cursor = parent
            while cursor is not None:
                assert cursor != key, 'intermediate cycle'
                cursor = parents.get(cursor)
            if key in parents:
                lists[parents[key]].remove(key)
            siblings = lists[parent]
            index = siblings.index(before) if before is not None else len(siblings)
            siblings.insert(index, key)
            parents[key] = parent
        elif op == 'patch_node':
            values = records[key][operation['field']]
            values.update(deepcopy(operation['set']))
            for name in operation['unset']:
                del values[name]
        elif op == 'remove_node':
            remove(key)
        elif op == 'put_binding':
            slots[operation['slot']['token']] = deepcopy(operation['slot'])
        elif op == 'remove_binding':
            del slots[operation['slot_token']]
        elif op == 'put_canvas':
            canvases[operation['frame']['node_id']] = deepcopy(operation['frame'])
        elif op == 'remove_canvas':
            del canvases[key]
        else:
            raise AssertionError(op)

    def build(key):
        result = deepcopy(records[key])
        result['children'] = [build(child) for child in lists[key]]
        return result

    assert set(parents) == set(records), 'detached node left over'
    return {'roots': [build(key) for key in lists[None]],
            'bindings': list(slots.values()), 'canvases': list(canvases.values())}


class DiffTests(unittest.TestCase):
    def assertTransition(self, before, after):
        before_copy, after_copy = deepcopy(before), deepcopy(after)
        result = apply(before, diff(before, after))
        self.assertTrue(same(result, after), (result, after))
        self.assertEqual(before, before_copy)
        self.assertEqual(after, after_copy)

    def test_move_out_of_deleted_ancestor_and_reverse_ancestry(self):
        self.assertTransition(state(node('old', node('kept'))), state(node('kept')))
        self.assertTransition(state(node('a', node('b'))), state(node('b', node('a'))))
        self.assertTransition(state(node('a', node('b', node('c')))),
                              state(node('c', node('b', node('a')))))
        self.assertTransition(state(node('a'), node('b'), node('c')),
                              state(node('c'), node('a'), node('b')))

    def test_values_resets_and_unchanged_tree(self):
        before = state(node('a', enabled=True))
        before['roots'][0]['children'][0]['style'] = {'color': '#ff0000'}
        after = state(node('a', enabled=1))
        self.assertTransition(before, after)
        operations = diff(before, after)
        self.assertEqual(len(operations), 2)
        self.assertEqual(operations[1]['unset'], ['color'])
        self.assertEqual(diff(after, after), [])

    def test_deterministic_random_forest_changes(self):
        rng = random.Random(193)
        def tree():
            keys = rng.sample([str(i) for i in range(18)], rng.randrange(19))
            root = node('window', kind='Window')
            parents = [root]
            for key in keys:
                item = node(key, text=str(rng.randrange(3)))
                rng.choice(parents)['children'].append(item)
                parents.append(item)
            return {'roots': [root], 'bindings': [], 'canvases': []}
        for index in range(300):
            with self.subTest(index=index):
                self.assertTransition(tree(), tree())

    def test_binding_lifetime_and_canvas_removal(self):
        before = state(node('field', kind='TextField'), node('canvas', kind='Canvas'))
        ref = {'object_id': '12345678901234567890', 'kind': 'attr', 'key': 'value'}
        slot = {'token': 'slot1', 'ref': ref, 'value_rev': 1, 'value': 'hello'}
        before['bindings'] = [slot]
        before['roots'][0]['children'][0]['bindings']['model'] = {
            'ref': ref, 'slot_token': 'slot1', 'token': 'attachment1', 'writable': True}
        before['canvases'] = [{'node_id': 'canvas', 'frame_rev': 1}]
        self.assertTransition(before, state(node('canvas', kind='Canvas')))
        self.assertTransition(before, state())
        after = deepcopy(before)
        after['bindings'][0].update(value='goodbye', value_rev=2)
        self.assertTransition(before, after)
        after['bindings'][0]['value_rev'] = 1
        with self.assertRaises(ProtocolError):
            diff(before, after)

    def test_invalid_identity_and_ownership(self):
        for target in (state(node('a'), node('a')), state(node('a', kind='Label'))):
            with self.assertRaises(ProtocolError):
                diff(state(node('a')), target)
        target = state()
        target['canvases'] = [{'node_id': 'missing'}]
        with self.assertRaises(ProtocolError):
            diff(state(), target)


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.stream = RenderStream()

    def ack(self, body, status='applied', applied_rev=None):
        return self.stream.acknowledge(render_rev=body['rev'],
            applied_rev=body['rev'] if applied_rev is None else applied_rev, status=status)

    def test_coalesces_against_acked_state_and_retries_immutable_body(self):
        first = state(node('label', text='one'))
        self.stream.offer(first, processed_seq=1)
        snapshot = self.stream.next_render()
        saved = deepcopy(snapshot)
        first['roots'].clear()
        snapshot['roots'].clear()
        self.assertEqual(self.stream.retry(), saved)
        self.stream.offer(state(node('label', text='two')), processed_seq=2)
        self.stream.offer(state(node('label', text='three')), processed_seq=3)
        self.assertIsNone(self.stream.next_render())
        self.assertTrue(self.ack(snapshot))
        patch = self.stream.next_render()
        self.assertEqual(patch['base_rev'], saved['rev'])
        self.assertEqual(patch['processed_seq'], 3)
        self.assertEqual(apply({key: saved[key] for key in ('roots', 'bindings', 'canvases')},
                               patch['ops']), state(node('label', text='three')))
        self.assertFalse(self.ack(snapshot))
        self.assertIsNone(self.stream.next_render())
        self.assertTrue(self.ack(patch))
        self.assertIsNone(self.stream.next_render())

    def test_noop_edit_still_advances_processed_seq(self):
        target = state(node('field', kind='TextField', text='unchanged'))
        self.stream.offer(target, processed_seq=1)
        self.ack(self.stream.next_render())
        self.stream.offer(target, processed_seq=7)
        patch = self.stream.next_render()
        self.assertEqual(patch['ops'], [])
        self.assertEqual(patch['processed_seq'], 7)

    def test_discard_waits_for_resync_and_does_not_adopt_unknown_baseline(self):
        self.stream.offer(state(), processed_seq=1)
        initial = self.stream.next_render()
        self.ack(initial, status='discarded', applied_rev=0)
        self.assertIsNone(self.stream.next_render())
        self.stream.resync(last_applied_rev=0)
        self.stream.resync(last_applied_rev=0)
        recovery = self.stream.next_render()
        self.assertEqual(recovery['mode'], 'snapshot')
        self.assertGreater(recovery['rev'], initial['rev'])
        self.stream.resync(last_applied_rev=0)
        self.assertFalse(self.ack(initial, status='discarded', applied_rev=0))
        self.assertTrue(self.ack(recovery))
        self.assertIsNone(self.stream.next_render())

    def test_resync_waits_for_existing_credit_and_future_ack_fails(self):
        self.stream.offer(state(), processed_seq=1)
        first = self.stream.next_render()
        self.ack(first)
        self.stream.offer(state(), processed_seq=2)
        pending = self.stream.next_render()
        self.stream.resync(last_applied_rev=first['rev'])
        self.assertIsNone(self.stream.next_render())
        self.ack(pending, status='discarded', applied_rev=first['rev'])
        self.assertEqual(self.stream.next_render()['mode'], 'snapshot')
        with self.assertRaises(ProtocolError):
            self.stream.acknowledge(render_rev=100, applied_rev=100, status='applied')
        with self.assertRaises(ProtocolError):
            self.stream.offer(state(), processed_seq=0)


if __name__ == '__main__':
    unittest.main()
