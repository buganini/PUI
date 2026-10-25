"""Shared browser code must import without loading a backend or its codecs."""
from pathlib import Path
import subprocess
import sys
import unittest


class BrowserImportBoundary(unittest.TestCase):
    def test_schema_without_backend_or_site_packages(self):
        result = subprocess.run([sys.executable, '-S', '-c', '''
import importlib.abc
import sys

class DenyBackends(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('PUI.web', 'PUI.pyodide')) or fullname.split('.')[0] in (
                'aiohttp', 'msgpack', 'zstandard', 'pyodide'):
            raise AssertionError('Shared code imported ' + fullname)

sys.meta_path.insert(0, DenyBackends())
from PUI._browser.schema import RenderLimits, validate_data
from PUI._browser.messages import validate_client_body
from PUI._browser import widgets, runtime, render, canvas, table, images
validate_data({'text': 'Hello', 'values': [True, 1, None]}, limits=RenderLimits())
validate_client_body('ack', {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
'''], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_web_reexports_shared_validation(self):
        from PUI._browser import schema
        from PUI.web import protocol
        self.assertIs(protocol.ProtocolError, schema.ProtocolError)
        self.assertIs(protocol.validate_data, schema.validate_data)
        for key, value in schema.RenderLimits().__dict__.items():
            self.assertEqual(getattr(protocol.Limits(), key), value)

    def test_web_widgets_are_shared_classes(self):
        from PUI import web
        from PUI._browser import widgets
        from PUI._browser.images import ImageResource
        for name in ('PUIView', 'Window', 'Label', 'TextField', 'TextEdit', 'MaskedField',
                     'ComboBox', 'Table', 'Canvas', 'Tabs', 'Views'):
            self.assertIs(getattr(web, name), getattr(widgets, name))
        self.assertIs(web.ImageResource, ImageResource)
        self.assertTrue(issubclass(web.Application, widgets.Application))

    def test_pyodide_without_web_or_site_packages(self):
        result = subprocess.run([sys.executable, '-S', '-c', '''
import sys
from PUI import pyodide
from PUI.pyodide.runtime import Runtime
from PUI._browser import widgets
assert pyodide.Canvas is widgets.Canvas
assert pyodide.Table is widgets.Table
assert pyodide.TextEdit is widgets.TextEdit
assert issubclass(pyodide.Application, widgets.Application)
assert not any(name in sys.modules for name in (
    'PUI.web', 'aiohttp', 'msgpack', 'zstandard', 'PySide6', 'multiprocessing'))
'''], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
