import asyncio
import unittest
from PUI.web import Application, Window, VBox, Label, State, PUIView
from PUI.web.runtime import Runtime
from PUI.adaptive import matches


class AdaptiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_wide_overrides_restore_and_retain_native_node(self):
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        Label('responsive').layout(width=100, padding=2).style(
                            color=0x111111, fontSize=12,
                        ).wideLayout(600, width=200, weight=0, padding=8).wideStyle(
                            600, color=0, fontSize=18,
                        ).wideLayout(800, width=300).wideLayout(600, height=30).tWideLayout(
                            1, width=999,
                        ).tWideStyle(1, color=0xFFFFFF)
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            parent = runtime.app.children[0].children[0]
            original = parent.children[0]
            native, key = original.ui, original.key
            for width in (599, 600, 800, 400, 600):
                parent.get_node()._set_size(width, 400)
                runtime.flush()
                child = parent.get_node().children[0]
                self.assertIs(child.ui, native)
                self.assertEqual(child.key, key)
                self.assertEqual(child.layout_width, 300 if width >= 800 else 200 if width >= 600 else 100)
                self.assertEqual(child.layout_height, 30 if width >= 600 else None)
                self.assertEqual(child.layout_weight, 0 if width >= 600 else None)
                self.assertEqual(child.style_color, 0 if width >= 600 else 0x111111)
                self.assertEqual(child.style_fontsize, 18 if width >= 600 else 12)
        finally:
            runtime.close()

    async def test_direction_switch_retains_children(self):
        from PUI.web import HVBox, VHBox, TextField
        class Example(Application):
            def setup(self):
                self.form = State()
                self.form.value = 'retained'
            def content(self):
                with Window():
                    with VBox() as parent:
                        with HVBox(600):
                            TextField(self.form('value'))
                        with VHBox(400):
                            Label('second')
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            parent = runtime.app.children[0].children[0]
            boxes = parent.children
            native = [box.ui for box in boxes]
            field = boxes[0].children[0].ui
            keys = [box.key for box in boxes]
            self.assertEqual([box.container_x for box in boxes], [False, True])
            for width, height in [(600,400),(599,399),(900,700),(400,200)]:
                parent._set_size(width, height)
                runtime.flush()
                boxes = parent.get_node().children
                self.assertEqual([box.container_x for box in boxes], [width>=600,height<400])
                self.assertEqual([box.key for box in boxes], keys)
                self.assertEqual([box.ui for box in boxes], native)
                self.assertIs(boxes[0].children[0].ui, field)
                self.assertEqual(boxes[0].properties()['direction'], 'row' if width>=600 else 'column')
        finally:
            runtime.close()

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
                        with VBox().visible(minWidth=600):
                            Content()
                        with VBox().visible(maxWidth=600):
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
                with Window(size=(1024, 768)) as window:
                    binding = window.size()
                    bindings.append(binding)
                    Label(str(binding.value))
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            root = runtime.snapshot()['roots'][0]
            self.assertTrue(root['layout']['observe_size'])
            self.assertNotIn('width', root['layout'])
            self.assertNotIn('height', root['layout'])
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

    async def test_graphical_backends_ignore_terminal_options(self):
        runtime = Runtime(asyncio.get_running_loop())
        try:
            class Example(Application):
                def content(self):
                    with Window():
                        box = VBox().tLayout(width=10, height=3).tStyle(color=0xFF0000)
                        box.visible(tMaxWidth=1, tMaxHeight=1)
                        self.box = box
            runtime.app = Example()
            runtime.app.sync()
            box = runtime.app.box
            self.assertIsNone(box.tsize().value)
            self.assertIsNone(box._state)
            self.assertTrue(box._visible)
            self.assertIsNone(box.layout_width)
            self.assertIsNone(box.style_color)
        finally:
            runtime.close()

    def test_bounds(self):
        self.assertFalse(matches(None, (None, None, None, None)))
        self.assertTrue(matches((0, 0), (0, 1, 0, 1)))
        self.assertFalse(matches((600, 200), (None, 600, None, None)))
        self.assertTrue(matches((600, 200), (600, None, 200, 201)))
