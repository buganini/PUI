"""Declarative visibility uses ordinary State reads and retains browser elements."""
import asyncio
import unittest
from PUI.web import Application, Window, VBox, Label, State
from PUI.web.runtime import Runtime


class VisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_state_read_updates_visibility_without_replacing_element(self):
        class Example(Application):
            def setup(self):
                self.state = State()
                self.state.show = True
            def content(self):
                with Window():
                    with VBox():
                        Label('Toggle').visible(self.state.show)
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            runtime.flush()
            label = runtime.app.children[0].children[0].children[0]
            element = label.ui
            for shown in (False, True, False):
                runtime.app.state.show = shown
                runtime.flush()
                snapshot = runtime.snapshot()
                label = runtime.app.children[0].children[0].children[0]
                self.assertIs(label.ui, element)
                wire = snapshot['roots'][0]['children'][0]['children'][0]
                self.assertEqual(wire['layout'].get('visible', True), shown)
        finally:
            runtime.close()
