"""Hot-reload startup must not expose a partially initialized PUI API."""
import subprocess
import sys
import unittest
from pathlib import Path


class ImportInitializationTests(unittest.TestCase):
    def test_backend_import_during_watcher_initialization(self):
        result = subprocess.run([sys.executable, '-c', '''
import importlib
import sys
import types

watcher = types.ModuleType('jurigged')
def watch(path):
    import PUI
    assert hasattr(PUI, 'NotImplementedNode')
    modules = [importlib.import_module('PUI.PySide6.' + name)
               for name in ('window', 'combobox', 'textfield', 'table',
                            'image', 'tree', 'modal')]
    for module in modules:
        assert module.Prop is PUI.Prop, module.__name__
        prop = module.Prop()
        assert prop.set(1)
        assert not prop.set(1)
    return types.SimpleNamespace(
        postrun=types.SimpleNamespace(register=lambda callback: None))
watcher.watch = watch
sys.modules['jurigged'] = watcher
import PUI
'''], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
