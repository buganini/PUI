"""Grid track priorities and native geometry (wx/Tk require a display)."""
import contextlib
import importlib
import io
import unittest

from PUI.grid import track_stretches, native_stretches
from PUI.expansion import priority
from expansion import node


class GridPriorities(unittest.TestCase):
    def test_tracks_spans_hidden_children_and_weights(self):
        grid = node(pui_grid_layout=True)
        label = node(grid, x=0, y=0)
        field = node(grid, x=4, y=0)
        area = node(grid, x=4, y=4)
        weighted = node(grid, x=0, y=0, layout_weight=0.5)
        cells = [(label, (0, 0, 1, 1)), (field, (0, 2, 1, 1)),
                 (area, (1, 1, 2, 2)), (weighted, (3, 0, 1, 1))]
        self.assertEqual(track_stretches(cells, 'x', grid), [0.5, 0, 0])
        self.assertEqual(track_stretches(cells, 'y', grid), [0, 0, 0, 0.5])
        weighted.layout_weight = 0
        self.assertEqual(track_stretches(cells, 'x', grid), [0, 1, 1])
        self.assertEqual(track_stretches(cells, 'y', grid), [0, 1, 1, 0])
        area._visible = False
        self.assertEqual(track_stretches(cells, 'x', grid), [0, 0, 1])
        self.assertEqual(track_stretches(cells, 'y', grid), [0, 0, 0, 0])
        field._visible = False
        self.assertFalse(any(track_stretches(cells, 'x', grid)))
        self.assertEqual(native_stretches([0, 0.5, 1]), [0, 1, 2])

    def test_same_track_uses_maximum_not_sum_and_nested_demand(self):
        grid = node(pui_grid_layout=True)
        box = node(grid, x=1, y=1)
        view = node(box, virtual=True)
        field = node(view, x=4, y=0)
        plain = node(grid, x=1, y=1)
        cells = [(box, (0, 0, 1, 1)), (plain, (0, 1, 1, 1))]
        self.assertEqual(track_stretches(cells, 'x', grid), [1, 0])
        self.assertEqual(priority(box, 'x'), 2)
        field._visible = False
        self.assertEqual(track_stretches(cells, 'x', grid), [1, 1])
        box.layout_weight, plain.layout_weight = 2, 1
        cells.append((box, (1, 0, 1, 1)))
        self.assertEqual(track_stretches(cells, 'x', grid), [2, 1])


class NativeGridSizing(unittest.TestCase):
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

        class Demo(UI.Application):
            weight = None
            editors = True
            auto = False
            def content(self):
                with UI.Window(size=(700, 400)):
                    with UI.Grid().layout(weight=1, padding=0) as self.grid:
                        if self.auto:
                            self.grid.columns(3, expandChildren=False)
                        UI.Label('Field').id('label').grid(row=0, column=0).layout(weight=self.weight)
                        UI.Label('Value').id('value').grid(row=0, column=1)
                        UI.TextField(UI.DummyBinding('input')).id('input').grid(row=0, column=2).visible(self.editors)
                        UI.Label('Body').id('body-label').grid(row=1, column=0, columnspan=2)
                        UI.TextEdit(UI.DummyBinding('body')).id('body').grid(row=1, column=2).visible(self.editors)
                        UI.Label('Footer').id('footer').grid(row=2, column=0, columnspan=3)

        root = Demo()
        if backend == 'PySide6':
            root.ui = app
        def pump():
            for _ in range(4):
                if backend == 'PySide6': app.processEvents()
                elif backend == 'wx': app.Yield(); app.ProcessPendingEvents()
                else: root.ui.update()
        def sync():
            output = io.StringIO()
            with contextlib.redirect_stdout(output): root.sync()
            self.assertNotIn('<ERROR', output.getvalue())
            pump()
        def item(name):
            return next(child for child in root.grid.children if child._id == name).ui
        def extent(name):
            widget = item(name)
            if backend == 'PySide6': return widget.width(), widget.height()
            if backend == 'wx': return tuple(widget.GetSize())
            return widget.winfo_width(), widget.winfo_height()
        try:
            sync()
            editor = item('input')
            compact = extent('label'), extent('value'), extent('footer')[1]
            self.assertLess(compact[0][0], 120)
            self.assertGreater(extent('input')[0], 300)
            self.assertLess(extent('input')[1], 80)
            self.assertGreater(extent('body')[1], 150)
            root.auto = True
            sync()
            self.assertEqual(extent('label'), compact[0])
            self.assertGreater(extent('input')[0], 300)
            root.auto = False
            root.weight = 2
            sync()
            self.assertGreater(extent('label')[0], compact[0][0] + 100)
            self.assertGreater(extent('label')[1], compact[0][1] + 40)
            root.weight = 0
            sync()
            self.assertEqual(extent('label'), compact[0])
            self.assertIs(item('input'), editor)
            root.editors = False
            sync()
            self.assertLess(extent('footer')[0], 180)
            self.assertEqual(extent('footer')[1], compact[2])
            root.editors = True
            sync()
            self.assertIs(item('input'), editor)
            self.assertGreater(extent('input')[0], 300)
        finally:
            if backend == 'PySide6':
                root.ui = None  # The test suite owns the shared QApplication.
            recur_delete(root, root, True)
            if backend == 'PySide6': app.processEvents()

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
