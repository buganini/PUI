"""State transactions serialize threads and notify only after releasing the lock."""
import threading
import time
import unittest
from collections import defaultdict
from unittest.mock import Mock

from PUI import PUIView, State, StateDict, StateList, StateMutationInViewBuilderError, Unstate


class StateThreadingTests(unittest.TestCase):
    def spawn(self, operation):
        started, done = threading.Event(), threading.Event()
        result, errors = [], []

        def run():
            started.set()
            try:
                result.append(operation())
            except BaseException as error:
                errors.append(error)
            finally:
                done.set()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.assertTrue(started.wait(2))
        return thread, done, result, errors

    def finish(self, task):
        thread, done, result, errors = task
        self.assertTrue(done.wait(3), 'State operation remained blocked')
        thread.join(1)
        if errors:
            raise errors[0]
        return result[0]

    def observe(self, read):
        class Observer(PUIView):
            def content(self):
                read()
        view = Observer()
        self.addCleanup(view.destroy, True)
        view.sync()
        view.redraw = Mock()
        return view

    def test_nested_transactions_batch_all_nested_containers(self):
        state = State()
        state.count = 0
        state.rows = State([{'name': 'before'}], deep=True)
        child = state.rows[0]
        view = self.observe(lambda: (state.count, child['name']))
        changes = []
        child('name').change(changes.append)
        with state:
            state.count = 1
            with state:
                with child:
                    child['name'] = 'one'
                child['name'] = 'two'
            view.redraw.assert_not_called()
            self.assertEqual(changes, [])
        view.redraw.assert_called_once()
        self.assertEqual(changes, ['one', 'two'])

    def test_reentrant_callbacks_follow_pending_changes_before_redraw(self):
        state = State()
        state.value = state.mirror = 0
        view = self.observe(lambda: (state.value, state.mirror))
        seen = []

        def changed(value):
            if value == 1:
                state.value = 3
            seen.append(value)
            state.mirror = value

        state('value').change(changed)
        with state:
            state.value = 1
            state.value = 2
        self.assertEqual(seen, [1, 2, 3])
        self.assertEqual((state.value, state.mirror), (3, 3))
        view.redraw.assert_called_once()

    def test_binding_reads_and_writes_wait_for_transaction(self):
        obj = State()
        obj.value = 0
        for state, key in ((obj, 'value'), (State({'value': 0}), 'value'), (State([0]), 0)):
            with self.subTest(state=type(state).__name__):
                binding = state(key)
                with state:
                    writer = self.spawn(lambda: setattr(binding, 'value', 7))
                    reader = self.spawn(lambda: binding.value)
                    self.assertFalse(writer[1].wait(.05))
                    self.assertFalse(reader[1].wait(.05))
                self.finish(writer)
                self.assertIn(self.finish(reader), (0, 7))
                self.assertEqual(binding.value, 7)

    def test_existing_aliased_child_uses_the_transaction_lock(self):
        child = StateList([0])
        first, second = State(), State()
        first.child = second.child = child
        with first:
            with second:
                task = self.spawn(lambda: child.append(1))
                self.assertFalse(task[1].wait(.05))
            self.assertFalse(task[1].wait(.05))
        self.finish(task)
        self.assertEqual(list(child), [0, 1])

    def test_read_modify_write_is_atomic(self):
        state = State({'left': 0, 'right': 0})
        barrier = threading.Barrier(4)

        def increment():
            barrier.wait(3)
            for _ in range(50):
                with state:
                    value = state['left']
                    self.assertEqual(value, state['right'])
                    time.sleep(0)  # Offer other threads a chance to enter.
                    state['left'] = value + 1
                    state['right'] = value + 1

        tasks = [self.spawn(increment) for _ in range(4)]
        for task in tasks:
            self.finish(task)
        self.assertEqual(Unstate(state), {'left': 200, 'right': 200})

    def test_unstate_waits_for_consistent_nested_snapshot(self):
        state = State({'nested': [{'value': 1}]}, deep=True)
        with state:
            state['nested'][0]['value'] = 2
            task = self.spawn(lambda: Unstate(state))
            self.assertFalse(task[1].wait(.05))
            state['nested'].append(State({'value': 3}))
        self.assertEqual(self.finish(task), {'nested': [{'value': 2}, {'value': 3}]})

    def test_callbacks_and_redraw_run_after_unlock(self):
        state = State({'value': 0})
        view = self.observe(lambda: state['value'])
        delivered = []

        def callback(value):
            delivered.append(self.finish(self.spawn(lambda: state['value'])))
        state('value').change(callback)
        view.redraw.side_effect = lambda: callback(None)
        state['value'] = 1
        self.assertEqual(delivered, [1, 1])
        with state:
            state['value'] = 2
            self.assertEqual(delivered, [1, 1])
        self.assertEqual(delivered, [1, 1, 2, 2])

    def test_exception_releases_lock_and_notifies_partial_changes(self):
        state = State({'value': 0})
        view = self.observe(lambda: state['value'])
        with self.assertRaisesRegex(ValueError, 'transaction failed'):
            with state:
                with state:
                    state['value'] = 1
                    raise ValueError('transaction failed')
        view.redraw.assert_called_once()
        self.assertEqual(self.finish(self.spawn(lambda: state['value'])), 1)
        with state:
            state['value'] = 2
        self.assertEqual(view.redraw.call_count, 2)

    def test_failing_callback_does_not_hide_body_error_or_skip_observers(self):
        state = State({'value': 0})
        view = self.observe(lambda: state['value'])
        received = []
        def fail(value):
            raise RuntimeError('observer failed')
        state('value').change(fail)
        state('value').change(received.append)
        with self.assertLogs('PUI.state', level='ERROR'):
            with self.assertRaisesRegex(ValueError, 'body failed'):
                with state:
                    state['value'] = 1
                    raise ValueError('body failed')
        self.assertEqual(received, [1])
        view.redraw.assert_called_once()
        self.assertEqual(self.finish(self.spawn(lambda: state['value'])), 1)
        with self.assertRaisesRegex(RuntimeError, 'observer failed'):
            state['value'] = 2
        self.assertEqual(received, [1, 2])
        self.assertEqual(view.redraw.call_count, 2)

    def test_iterators_and_dictionary_views_are_snapshots(self):
        items = State([1, 2])
        iterator = iter(items)
        items.clear()
        self.assertEqual(list(iterator), [1, 2])
        state = State({'a': 1, 'b': 2})
        keys, values, pairs, iterator = state.keys(), state.values(), state.items(), iter(state)
        state.clear()
        self.assertEqual(set(keys), {'a', 'b'})
        self.assertEqual(list(values), [1, 2])
        self.assertEqual(dict(pairs), {'a': 1, 'b': 2})
        self.assertEqual(list(iterator), ['a', 'b'])
        self.assertEqual(keys & {'a'}, {'a'})

    def test_copy_and_structural_callback_values_are_snapshots(self):
        mapping = StateDict(defaultdict(str, a=1))
        self.assertEqual(mapping['new'], '')
        copy = mapping.copy()
        mapping['a'] = 3
        self.assertEqual(copy['a'], 1)
        items, seen = StateList([1, 2]), []
        items(None)  # Explicit emit is also guarded.
        items(0).change(seen.append)
        with items:
            items.pop(0)
            items.append(3)
        self.assertEqual(seen, [[2]])

    def test_nested_state_object_can_be_observed_in_all_containers(self):
        child = State()
        child.value = 0
        obj = State()
        obj.child = child
        for parent, read in ((obj, lambda: obj.child),
                             (State([child]), None), (State({'child': child}), None)):
            if read is None:
                read = lambda parent=parent: parent[0 if isinstance(parent, StateList) else 'child']
            view = self.observe(read)
            child.value += 1
            view.redraw.assert_called_once()
            view.destroy(True)

    def test_view_builder_mutation_still_fails_and_releases_lock(self):
        state = State({'value': 0})
        view = PUIView()
        self.addCleanup(view.destroy, True)
        with view:
            with self.assertRaises(StateMutationInViewBuilderError):
                with state:
                    state['value'] = 1
        self.assertEqual(self.finish(self.spawn(lambda: state['value'])), 0)


if __name__ == '__main__':
    unittest.main()
