"""Public backend publishers remain replaceable after view construction."""
import asyncio
import importlib
import unittest
from unittest.mock import patch

import PUI
from PUI.state_refs import noop_publish


class BackendPublisherTests(unittest.TestCase):
    def test_native_backend_callbacks(self):
        for backend in ('PySide6', 'wx', 'tkinter', 'flet', 'textual'):
            with self.subTest(backend=backend):
                ui = importlib.import_module('PUI.' + backend)
                self.assertIs(ui.state_ref_publish, noop_publish)
                # Dispatch does not require creating native windows or event loops.
                for view_class in (ui.PUIView, ui.Application):
                    view = object.__new__(view_class)
                    state = PUI.State({'value': 'hello'})
                    binding = state('value')
                    with patch('PUI.state.find_puiview', return_value=view):
                        self.assertIs(binding.ref('example.value'), binding)
                        with patch.object(ui, 'state_ref_publish') as publish:
                            self.assertIs(binding.ref('example.value'), binding)
                            publish.assert_called_once_with('example.value', 'hello')
                self.assertIs(ui.state_ref_publish, noop_publish)


class PyodidePublisherTests(unittest.IsolatedAsyncioTestCase):
    async def test_pyodide_override_is_independent_of_web(self):
        import PUI.pyodide as UI
        from PUI.pyodide.runtime import Runtime

        class App(UI.Application):
            def setup(self):
                self.state = UI.State()
                self.state.value = 'first'

            def content(self):
                self.state('value').ref('example.value')

        runtime = Runtime(asyncio.get_running_loop(), lambda message: None,
                          epoch='test', build='test')
        try:
            self.assertIsNot(UI.state_ref_publish, noop_publish)
            runtime.app = App()
            runtime.app.sync()
            self.assertEqual(runtime.state_refs.snapshot(), {'example.value': '"first"'})
            with patch.object(UI, 'state_ref_publish') as publish, patch('PUI.web.state_ref_publish') as web:
                runtime.app.state.value = 'second'
                runtime.flush()
                publish.assert_called_once_with('example.value', 'second')
                web.assert_not_called()
        finally:
            runtime.close()


if __name__ == '__main__':
    unittest.main()
