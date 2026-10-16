"""All Canvas exports accept shared painter scopes without requiring a GUI."""
import importlib
import importlib.util
import unittest

from PUI._canvas import CanvasScope


class CanvasScopeTests(unittest.TestCase):
    def test_backend_exports_support_nested_noop_scopes(self):
        for backend, dependency in (('flet', 'flet'),
                                    ('tkinter', 'tkinter'), ('web', 'aiohttp'),
                                    ('pyodide', None), ('textual', 'textual')):
            with self.subTest(backend=backend):
                if dependency and importlib.util.find_spec(dependency) is None:
                    self.skipTest(dependency + " is not installed")
                module = importlib.import_module('PUI.' + backend)
                canvas = object.__new__(module.Canvas)
                self.assertIsInstance(canvas, CanvasScope)
                before = dict(canvas.__dict__)
                for method in (canvas.push, canvas.push, canvas.pop, canvas.pop):
                    self.assertIsNone(method())
                self.assertEqual(canvas.__dict__, before)


if __name__ == '__main__':
    unittest.main()
