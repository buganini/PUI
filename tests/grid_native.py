"""Native Grid reflow keeps controls mounted and their drafts intact."""
import importlib
import unittest


class NativeGrid(unittest.TestCase):
    def exercise(self, backend):
        UI = importlib.import_module('PUI.' + backend)
        from PUI.dom import recur_delete
        if backend == 'PySide6':
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication([])
            type(self)._qt_app = app
        elif backend == 'wx':
            import wx
            app = wx.GetApp() or wx.App(False)
            type(self)._wx_app = app
        model = UI.DummyBinding('retained')
        class Demo(UI.Application):
            columns = 3
            hidden = False
            reverse = False
            def content(self):
                with UI.Window(size=(600, 400)):
                    with UI.Grid().columns(self.columns, dense=True) as self.grid:
                        for name, span in ([('a', 2), ('b', 2), ('c', 1)][::(-1 if self.reverse else 1)]):
                            UI.Label(name).id(name).grid(columnspan=span).visible(not(self.hidden and name == 'a'))
                        UI.TextField(model).id('editor')
        root = Demo()
        if backend == 'PySide6':
            root.ui = app
        root.sync()
        grid = root.grid
        editor = grid.children[-1].ui
        if backend == 'PySide6':
            editor.setText('draft')
            read = editor.text
        elif backend == 'wx':
            editor.SetValue('draft')
            read = editor.GetValue
        else:
            grid.children[-1].variable.set('draft')
            read = editor.get
        self.assertEqual([node._grid_cell for node in grid.children[:3]],
                         [(0, 0, 1, 2), (1, 0, 1, 2), (0, 2, 1, 1)])
        for columns in (1, 3, 2, 3):
            root.columns = columns
            root.sync()
            self.assertIs(root.grid.children[-1].ui, editor)
            self.assertEqual(read(), 'draft')
            self.assertEqual(root.grid.children[0]._grid_cell[3], min(2, columns))
        root.hidden = True
        root.sync()
        self.assertIsNone(root.grid.children[0]._grid_cell)
        self.assertEqual(root.grid.children[1]._grid_cell[:2], (0, 0))
        root.reverse = True
        root.sync()
        self.assertIs(root.grid.children[-1].ui, editor)
        recur_delete(root, root, True)
        if backend == 'PySide6':
            app.processEvents()

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
