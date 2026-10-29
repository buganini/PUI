"""Check the arguments passed by each backend, without opening system pickers."""
import importlib.util
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class FilterAdapters(unittest.TestCase):
    cases = [(['txt', '.csv'], 'Files'), ({'Documents': ['txt', '.csv']}, 'Documents')]

    def test_pyside6(self):
        from PUI.PySide6 import dialog
        for value, label in self.cases:
            for helper, native in ((dialog.OpenFile, 'getOpenFileName'),
                                   (dialog.OpenFiles, 'getOpenFileNames'),
                                   (dialog.SaveFile, 'getSaveFileName')):
                with self.subTest(helper=helper.__name__, value=value), patch.object(dialog.QtWidgets.QFileDialog, native, return_value=('', '')) as method:
                    helper(types=value)
                    self.assertEqual(method.call_args.args[3], f'{label} (*.txt *.csv)')

    def test_wx(self):
        from PUI.wx import dialog
        for value, label in self.cases:
            for helper in (dialog.OpenFile, dialog.OpenFiles, dialog.SaveFile):
                with self.subTest(helper=helper.__name__, value=value), patch.object(dialog.wx, 'FileDialog') as method:
                    helper(types=value)
                    self.assertEqual(method.call_args.kwargs['wildcard'], f'{label}|*.txt;*.csv')

    def test_tkinter(self):
        from PUI.tkinter import dialog
        for value, label in self.cases:
            for helper, native in ((dialog.OpenFile, 'askopenfilename'),
                                   (dialog.OpenFiles, 'askopenfilenames'),
                                   (dialog.SaveFile, 'asksaveasfilename')):
                with self.subTest(helper=helper.__name__, value=value), patch.object(dialog.filedialog, native, return_value='') as method:
                    helper(types=value)
                    self.assertEqual(method.call_args.kwargs['filetypes'], [(label, ('*.txt', '*.csv'))])

    def test_textual(self):
        from PUI.textual import file_dialog as dialog
        def create(kind, factory):
            return factory(Future())
        with patch.object(dialog, '_show_dialog', side_effect=create):
            for value, _ in self.cases:
                for helper in (dialog.OpenFile, dialog.OpenFiles, dialog.SaveFile):
                    self.assertEqual(helper(types=value).patterns, ['*.txt', '*.csv'])

    def test_web(self):
        from PUI.web import dialog
        runtime = SimpleNamespace(file_picker=Mock(), file_upload_access=Mock(), uploads=Mock(), dialog=Mock())
        with patch.object(dialog.widgets, '_current_runtime', runtime):
            for value, _ in self.cases:
                for helper in (dialog.OpenFile, dialog.OpenFiles):
                    runtime.file_upload_access.reset_mock()
                    helper(types=value)
                    self.assertEqual(runtime.file_upload_access.call_args_list[0].args[0]['patterns'], ['*.txt', '*.csv'])

    def test_pyodide(self):
        # Load just this adapter on CPython; the JSPI call is the mocked boundary.
        path = Path(__file__).parents[1] / 'PUI/pyodide/dialog.py'
        spec = importlib.util.spec_from_file_location('PUI.pyodide.dialog', path)
        dialog = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dialog)
        runtime = SimpleNamespace(closed=False, uploads=SimpleNamespace(limits={}))
        with patch.object(dialog.widgets, '_current_runtime', runtime), patch.object(dialog, '_dialog', return_value=None) as method:
            for value, _ in self.cases:
                for helper in (dialog.OpenFile, dialog.OpenFiles):
                    helper(types=value)
                    self.assertEqual(method.call_args.kwargs['options']['patterns'], ['*.txt', '*.csv'])
            with self.assertRaises(TypeError):
                dialog.SaveFile(types='Text (*.txt)')
