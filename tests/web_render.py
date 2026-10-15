"""Record diff equivalence and ACK/recovery invariants without a browser mock."""
from copy import deepcopy
import random
import unittest
from unittest.mock import patch

from PUI.web import render
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
        elif op == 'patch_canvas':
            frame = deepcopy(operation['frame'])
            before = canvases[frame['node_id']]
            assert before['frame_rev'] == operation['base_frame_rev']
            commands = before['commands']
            start = operation['start']
            commands[start:start + operation['delete_count']] = frame['commands']
            frame['commands'] = commands
            canvases[frame['node_id']] = frame
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

    def test_diff_outputs_remain_detached_from_inputs(self):
        before = state(node('existing', values=[0]), node('canvas', kind='Canvas'))
        target = state(node('existing', values=[1]), node('new', values=[2]),
                       node('canvas', kind='Canvas'))
        target['canvases'] = [{'node_id': 'canvas', 'commands': [{'points': [[3, 4]]}]}]
        saved = deepcopy(target)
        operations = diff(before, target)
        target['roots'][0]['children'][0]['props']['values'].append(9)
        target['roots'][0]['children'][1]['props']['values'].append(9)
        target['canvases'][0]['commands'].clear()
        self.assertEqual(apply(before, operations), saved)
        changed = deepcopy(target)
        for op in operations:
            if op['op'] == 'patch_node':
                op['set']['values'].clear()
            elif op['op'] == 'create_node':
                op['node']['props']['values'].clear()
            elif op['op'] == 'put_canvas':
                op['frame']['commands'].clear()
        self.assertEqual(target, changed)

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

    def test_standalone_diff_revalidates_mutable_inputs(self):
        before, target = state(), state(node('label', value='valid'))
        self.assertTransition(before, target)
        target['roots'][0]['children'][0]['props']['value'] = float('nan')
        with self.assertRaises(ProtocolError):
            diff(before, target)


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

    def test_background_update_at_same_input_sequence_still_renders(self):
        first, changed = state(node('label', text='before')), state(node('label', text='after'))
        self.stream.offer(first, processed_seq=1, copy=False)
        self.ack(self.stream.next_render())
        self.stream.offer(changed, processed_seq=1, copy=False)
        updated = self.stream.next_render()
        self.assertEqual(updated['processed_seq'], 1)
        self.assertEqual(apply(first, updated['ops']), changed)
        self.ack(updated)
        self.stream.offer(deepcopy(changed), processed_seq=1, copy=False)
        self.assertIsNone(self.stream.next_render())

    def test_reuses_validated_indexes_through_coalescing_ack_retry_and_recovery(self):
        for copy in (False, True):
            with self.subTest(copy=copy), patch.object(render, '_index', wraps=render._index) as indexed:
                self.stream = RenderStream()
                first = state(node('a', node('b')))
                latest = state(node('b', node('a', text='latest')))
                self.stream.offer(first, processed_seq=1, copy=copy)
                initial = self.stream.next_render(copy=copy)
                self.stream.offer(state(node('discarded')), processed_seq=2, copy=copy)
                self.stream.offer(latest, processed_seq=3, copy=copy)
                # Invalid new states must still fail without replacing the latest valid offer.
                with self.assertRaises(ProtocolError):
                    self.stream.offer(state(node('duplicate'), node('duplicate')), processed_seq=4, copy=copy)
                self.assertEqual(self.stream.retry(), initial)
                self.assertIsNone(self.stream.next_render())
                self.ack(initial)
                changed = self.stream.next_render(copy=copy)
                self.assertEqual(changed['processed_seq'], 3)
                self.assertEqual(apply(first, changed['ops']), latest)
                self.assertEqual(self.stream.retry(), changed)
                self.ack(changed, status='discarded', applied_rev=initial['rev'])
                self.stream.resync(last_applied_rev=initial['rev'])
                recovered = self.stream.next_render(copy=copy)
                self.assertEqual({k: recovered[k] for k in latest}, latest)
                self.ack(recovered)
                self.assertIsNone(self.stream.next_render())
                # Four offers, including the rejected state; no re-indexing on diff/ACK/retry.
                self.assertEqual(indexed.call_count, 4)

    def test_cached_indexes_follow_owned_copies_after_caller_mutation(self):
        first = state(node('a', node('b', value=['before'])))
        target = state(node('b', node('a', value=['after'])))
        expected_first, expected_target = deepcopy(first), deepcopy(target)
        self.stream.offer(first, processed_seq=1)
        first['roots'][0]['children'].clear()
        initial = self.stream.next_render()
        self.assertEqual({k: initial[k] for k in expected_first}, expected_first)
        self.ack(initial)
        self.stream.offer(target, processed_seq=2)
        target['roots'][0]['children'][0]['children'][0]['props']['value'].clear()
        target['roots'].clear()
        changed = self.stream.next_render()
        self.assertEqual(apply(expected_first, changed['ops']), expected_target)
        self.ack(changed)
        # Exercise the retained target as the next indexed baseline too.
        final = state(node('a', value=['final']), node('c'))
        self.stream.offer(final, processed_seq=3)
        self.assertEqual(apply(expected_target, self.stream.next_render()['ops']), final)

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
