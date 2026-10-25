"""Native placement and editor retention when responsive grid rules change."""
import importlib
import unittest
from unittest.mock import patch
from PUI.node import PUINode
from PUI.dom import recur_delete


class NativeWideGrid(unittest.TestCase):
    def exercise(self, backend):
        UI = importlib.import_module('PUI.' + backend)
        app = None
        if backend == 'PySide6':
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication([])
            type(self)._app = app
        elif backend == 'wx':
            import wx
            type(self)._app = wx.GetApp() or wx.App(False)
        model = UI.DummyBinding('value')
        class Demo(UI.Application):
            def content(self):
                with UI.Window(size=(600, 400)):
                    with UI.Grid() as self.grid:
                        UI.TextField(model).grid(row=0, column=0).wideGrid(
                            600, row=1, column=1, columnspan=2).id('editor')
                        UI.Label('Other').grid(row=0, column=2)
        root = Demo()
        if app is not None:
            root.ui = app
        editor = None
        try:
            for width in (400, 600, 800, 400):
                with patch.object(PUINode, '_wide_matches', lambda node, threshold, terminal, method=None: not terminal and width >= threshold):
                    root.sync()
                field = next(n for n in root.grid.children if n._id == 'editor')
                if editor is None:
                    editor = field.ui
                    if backend == 'PySide6':
                        editor.setText('draft'); read = editor.text
                    elif backend == 'wx':
                        editor.SetValue('draft'); read = editor.GetValue
                    else:
                        field.variable.set('draft'); read = editor.get
                self.assertIs(field.ui, editor)
                self.assertEqual(read(), 'draft')
                expected = (1, 1, 1, 2) if width >= 600 else (0, 0, 1, 1)
                if backend == 'PySide6':
                    actual = root.grid.layout.getItemPosition(root.grid.layout.indexOf(field.outer))
                elif backend == 'wx':
                    item = next(item for node, item in root.grid.sizerItems if node.get_node() is field)
                    actual = (*item.GetPos(), *item.GetSpan())
                else:
                    info = editor.grid_info()
                    actual = tuple(info[k] for k in ('row', 'column', 'rowspan', 'columnspan'))
                self.assertEqual(tuple(actual), expected)
        finally:
            if app is not None:
                root.ui = None
            recur_delete(root, root, True)

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
