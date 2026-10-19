import asyncio
import unittest
from PUI.web import Application, Window, VBox, Label, State, PUIView
from PUI.web.runtime import Runtime
from PUI.adaptive import matches


class AdaptiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_lazy_inheritance_breakpoints_and_thaw(self):
        built = []
        class Content(PUIView):
            def setup(self):
                built.append(1)
            def content(self):
                Label('retained')
        class Example(Application):
            def content(self):
                with Window():
                    with VBox().id('container') as container:
                        with VBox().visible(min_width=600):
                            Content()
                        with VBox().visible(max_width=600):
                            Label('compact')
                    Label('unobserved')
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            container = runtime.app.children[0].children[0]
            self.assertIsNone(runtime.app.children[0]._state)
            self.assertIsNone(runtime.app.children[0].children[1]._state)
            self.assertEqual(built, [])
            original = container
            state = container._state
            original._set_size(700, 400)
            runtime.flush()
            container = runtime.app.children[0].children[0]
            self.assertIs(container._state, state)
            self.assertTrue(container.children[0]._visible)
            self.assertFalse(container.children[1]._visible)
            self.assertEqual(len(built), 1)
            retained = container.children[0].children[0]
            original._set_size(710, 400)
            self.assertTrue(runtime._dirty)
            runtime.flush()
            original._set_size(710, 400)
            self.assertFalse(runtime._dirty)
            original._set_size(599, 400)
            runtime.flush()
            container = runtime.app.children[0].children[0]
            self.assertFalse(container.children[0]._visible)
            self.assertTrue(container.children[1]._visible)
            original._set_size(600, 400)
            runtime.flush()
            container = runtime.app.children[0].children[0]
            self.assertIs(container.children[0].children[0], retained)
            self.assertTrue(container.children[0]._visible)
        finally:
            runtime.close()
        self.assertIsNone(original.get_node()._size_cleanup)

    async def test_size_binding_survives_declarations_and_wire_measurement(self):
        bindings = []
        class Example(Application):
            def content(self):
                with Window() as window:
                    binding = window.size()
                    bindings.append(binding)
                    Label(str(binding.value))
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            root = runtime.snapshot()['roots'][0]
            self.assertTrue(root['layout']['observe_size'])
            self.assertTrue(runtime.size_control(dict(node_id=root['id'], width=800, height=600)))
            runtime.flush()
            self.assertIs(bindings[0].state, bindings[-1].state)
            self.assertEqual(bindings[-1].value, (800, 600))
            self.assertEqual(runtime.snapshot()['roots'][0]['children'][0]['props']['text'], '(800, 600)')
            self.assertFalse(runtime.size_control(dict(node_id='removed', width=1, height=1)))
        finally:
            runtime.close()

    async def test_sibling_size_bindings_remain_distinct_and_mutation_is_guarded(self):
        from PUI import StateMutationInViewBuilderError
        class Example(Application):
            def content(self):
                self.bindings = []
                with Window():
                    for i in range(2):
                        with VBox() as box:
                            self.bindings.append(box.size())
                            Label(str(box.size().value))
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            first, second = runtime.app.children[0].children
            first._set_size(100, 200)
            second._set_size(300, 400)
            runtime.flush()
            self.assertIsNot(runtime.app.bindings[0].state, runtime.app.bindings[1].state)
            self.assertEqual([b.value for b in runtime.app.bindings], [(100, 200), (300, 400)])
            with runtime.app, self.assertRaises(StateMutationInViewBuilderError):
                runtime.app.bindings[0].state.size = (1, 2)
        finally:
            runtime.close()

    async def test_resize_callback_tracks_replacements_and_cleanup_runs_once(self):
        callbacks, removed = [], []
        class Container(VBox):
            def _observe_size(self):
                callbacks.append(self._set_size)
                return lambda: removed.append(True)
        class Example(Application):
            present = True
            def content(self):
                with Window():
                    if self.present:
                        with Container() as container:
                            Label(str(container.size().value))
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            original = runtime.app.children[0].children[0]
            for width in (100, 200, 300):
                callbacks[0](width, 400)
                runtime.flush()
                current = runtime.app.children[0].children[0]
                self.assertIs(original.get_node(), current)
                self.assertEqual(current._state.size, (width, 400))
                self.assertEqual(len(callbacks), 1)
                self.assertEqual(removed, [])
            runtime.app.present = False
            runtime.app.sync()
            self.assertEqual(removed, [True])
            callbacks[0](999, 999)
            self.assertEqual(current._state.size, (300, 400))
        finally:
            runtime.close()
        self.assertEqual(removed, [True])

    def test_invalid_container_measurements_are_rejected(self):
        from PUI._browser.messages import validate_client_body
        from PUI._browser.schema import ProtocolError
        for width in (-1, float('nan'), float('inf'), True, '100', 1000001):
            with self.subTest(width=width), self.assertRaises(ProtocolError):
                validate_client_body('container_size', dict(node_id='n1', width=width, height=100))

    def test_bounds(self):
        self.assertFalse(matches(None, (None, None, None, None)))
        self.assertTrue(matches((0, 0), (0, 1, 0, 1)))
        self.assertFalse(matches((600, 200), (None, 600, None, None)))
        self.assertTrue(matches((600, 200), (600, None, 200, 201)))
