"""Named State subscriptions use view lifetimes without changing node refs."""
import asyncio
import gc
import json
import unittest
import weakref

import PUI
from PUI.web import Application, PUIView, Window, Label, State
from PUI.web.runtime import Runtime
from PUI.state_refs import StateRefs


class Child(PUIView):
    def setup(self):
        self.state = State()
        self.state.count = 0
        self.state.enabled = True

    def content(self):
        if self.state.enabled:
            self.state('count').ref('example.child')
        Label('Child')


class App(Application):
    def setup(self):
        self.state = State()
        self.state.text = 'Hello'
        self.state.show_child = True
        self.state.nested = State({'items': [1, {'value': 2}]}, deep=True)
        self.items = State([1, 'text'])
        self.mapping = State({'a': True})

    def content(self):
        self.state('text').ref('example.text')
        self.state('nested').ref('example.nested')
        self.items(0).ref('example.item')
        self.mapping('a').ref('example.flag')
        with Window():
            Label('Node ref').ref('example.text')
            if self.state.show_child:
                Child()


class StateRefTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.app = self.runtime.app

    async def asyncTearDown(self):
        self.runtime.close()

    def values(self):
        self.runtime.flush()
        return {name: json.loads(value) for name, value in self.runtime.state_refs.snapshot().items()}

    def child(self):
        return self.app.children[0].children[1]

    def test_typed_values_and_existing_binding_notifications(self):
        self.assertEqual(self.values(), {'example.text': 'Hello', 'example.nested':
            {'items': [1, {'value': 2}]}, 'example.item': 1, 'example.flag': True, 'example.child': 0})
        self.assertEqual(PUI.ref('example.text').node.text, 'Node ref')
        self.app.state.text = '世界 # = &'
        self.app.items[0] = 7
        self.app.mapping['a'] = False
        self.app.state.nested['items'][1]['value'] = 9
        self.assertEqual(self.values()['example.nested'], {'items': [1, {'value': 9}]})
        self.assertEqual(self.values()['example.text'], '世界 # = &')
        self.assertEqual(self.values()['example.item'], 7)
        self.assertIs(self.values()['example.flag'], False)

    def test_independent_subview_and_subscription_removal(self):
        child = self.child()
        child.state.count = 3
        self.assertEqual(self.values()['example.child'], 3)
        self.assertEqual(self.values()['example.text'], 'Hello')
        child.state.enabled = False
        self.assertNotIn('example.child', self.values())
        child.state.enabled = True
        self.assertEqual(self.values()['example.child'], 3)
        self.app.state.show_child = False
        self.assertNotIn('example.child', self.values())
        self.runtime.close()
        self.assertEqual(self.runtime.state_refs.snapshot(), {})

    def test_ref_returns_binding_and_is_noop_outside_web_content(self):
        binding = self.app.state('text')
        self.assertIs(binding.ref('example.outside'), binding)
        self.assertNotIn('example.outside', self.values())
        for name in ('', None, 1):
            with self.assertRaises(ValueError):
                binding.ref(name)
        native = PUI.PUIView()
        try:
            with native:
                self.assertIs(binding.ref('example.native'), binding)
            self.assertNotIn('example.native', self.values())
        finally:
            native.destroy(True)


class RegistryTests(unittest.TestCase):
    def test_last_declaration_wins_and_weak_ownership(self):
        class View:
            destroyed = False
            retired_by = None
        a, b = View(), View()
        refs = StateRefs()
        with refs.collect(a):
            refs.publish(a, 'same', 1)
            refs.publish(a, 'same', 2)
        with refs.collect(b):
            refs.publish(b, 'same', 3)
        self.assertEqual(refs.snapshot(), {'same': '3'})
        with self.assertRaises(RuntimeError), refs.collect(a):
            refs.publish(a, 'same', 99)
            raise RuntimeError('Failed view build')
        self.assertEqual(refs.snapshot(), {'same': '3'})
        with refs.collect(a):
            refs.publish(a, 'same', 4)
        self.assertEqual(refs.snapshot(), {'same': '4'})
        with self.assertRaises(RuntimeError), refs.collect(a):
            refs.publish(a, 'same', 5)
            raise RuntimeError('Failed view build')
        self.assertEqual(refs.snapshot(), {'same': '4'})
        ref = weakref.ref(a)
        del a
        gc.collect()
        self.assertIsNone(ref())
        self.assertEqual(refs.snapshot(), {'same': '3'})
        b.destroyed = True
        self.assertEqual(refs.snapshot(), {})

    def test_non_json_values_warn_and_do_not_break_other_subscriptions(self):
        class View:
            destroyed = False
            retired_by = None
        view, refs = View(), StateRefs()
        cyclic = []
        cyclic.append(cyclic)
        with refs.collect(view):
            for value in (object(), float('nan'), cyclic):
                with self.assertLogs('PUI', level='WARNING'):
                    refs.publish(view, 'invalid', value)
            refs.publish(view, 'valid', {'x': [None, True, 'hello']})
        self.assertEqual(refs.snapshot(), {'valid': '{"x":[null,true,"hello"]}'})


if __name__ == '__main__':
    unittest.main()
