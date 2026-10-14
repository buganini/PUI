"""Structural binding lifetimes must change even during batched notifications."""
import unittest
from unittest.mock import Mock
from PUI import State, PUIView, StateMutationInViewBuilderError


class BindingLifetimeTests(unittest.TestCase):
    def test_list_structural_operations_revoke_every_index(self):
        for operation in (lambda s: s.append('c'), lambda s: s.extend(['c']),
                lambda s: s.insert(1, 'c'), lambda s: s.pop(), lambda s: s.remove('a'),
                lambda s: s.reverse(), lambda s: s.sort(reverse=True), lambda s: s.clear()):
            with self.subTest(operation=operation):
                state = State(['a', 'b'])
                before = state._binding_generation(0)
                with state:
                    operation(state)
                    self.assertGreater(state._binding_generation(0), before)
                    self.assertEqual(state._binding_generation(0), state._binding_generation(-1))
        state = State(['a', 'b'])
        before = state._binding_generation(0)
        state[0] = 'new value'
        self.assertEqual(state._binding_generation(0), before)

    def test_partial_extend_failure_revokes_bindings(self):
        def values():
            yield 'b'
            raise ValueError('iterator failed')
        state = State(['a'])
        before = state._binding_generation(0)
        with self.assertRaises(ValueError):
            state.extend(values())
        self.assertEqual(list(state), ['a', 'b'])
        self.assertGreater(state._binding_generation(0), before)

    def test_dictionary_tracks_key_lifetimes_without_tombstones(self):
        state = State({'keep': 1, 'replace': 2})
        keep = state._binding_generation('keep')
        for remove in (lambda s: s.pop('replace'), lambda s: s.__delitem__('replace'), lambda s: s.popitem()):
            before = state._binding_generation('replace')
            with state:
                remove(state)
                self.assertIsNone(state._binding_generation('replace'))
                state.setdefault('replace', 3)
                self.assertNotEqual(state._binding_generation('replace'), before)
            self.assertEqual(state._binding_generation('keep'), keep)
        before = state._binding_generation('replace')
        state.update({'replace': 4}, extra=5)
        self.assertEqual(state._binding_generation('replace'), before)
        self.assertIsNotNone(state._binding_generation('extra'))
        state.clear()
        self.assertEqual(state._StateDict__generations, {})
        state['keep'] = 1
        self.assertNotEqual(state._binding_generation('keep'), keep)

    def test_dictionary_update_notifies_and_preserves_partial_failure(self):
        state = State({'a': 1})
        class Example(PUIView):
            def content(self):
                state['a']
        view = Example()
        try:
            view.sync()
            view.redraw = Mock()
            state.update(a=2)
            view.redraw.assert_called_once()
            def pairs():
                yield 'b', 3
                raise ValueError('pairs failed')
            with self.assertRaises(ValueError):
                state.update(pairs())
            self.assertEqual(state['b'], 3)
            self.assertIsNotNone(state._binding_generation('b'))
            self.assertEqual(view.redraw.call_count, 2)
            with view, self.assertRaises(StateMutationInViewBuilderError):
                state.popitem()
        finally:
            view.destroy(True)
