"""Shared tab placement contract across backends."""
import importlib
import inspect
import unittest
from unittest.mock import patch

from PUI import Side


class TabSideTests(unittest.TestCase):
    def test_backend_contract(self):
        import PUI.web  # Initialize the shared browser package before patching.
        for backend in ('PySide6', 'wx', 'tkinter', 'flet', 'textual', 'web', 'pyodide'):
            with self.subTest(backend=backend), patch('PUI._browser.widgets._current_runtime', object()):
                ui = importlib.import_module('PUI.' + backend)
                self.assertIs(ui.Side, Side)
                self.assertIs(inspect.signature(ui.Tabs).parameters['tabposition'].default, Side.TOP)
                for old in ('NORTH', 'SOUTH', 'EAST', 'WEST'):
                    self.assertFalse(hasattr(ui.Tabs, old))
                for old in ('n', 'e', 's', 'w', 'top', None):
                    with self.assertRaises(TypeError):
                        ui.Tabs(tabposition=old)
                for side in Side:
                    if backend in ('flet', 'textual') and side in (Side.LEFT, Side.RIGHT):
                        with self.assertRaises(NotImplementedError):
                            ui.Tabs(tabposition=side)
                    else:
                        node = ui.Tabs(tabposition=side)
                        self.assertIs(node.tabposition, side)
                        if backend in ('web', 'pyodide'):
                            node.selected = None
                            self.assertEqual(node.properties()['position'], side.value)
