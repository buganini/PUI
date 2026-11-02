"""Native Grid compact cells and explicit weight; run each backend separately."""
import importlib
import unittest
from PUI.dom import recur_delete


class GridCellExpansion(unittest.TestCase):
    def exercise(self, backend):
        ui = importlib.import_module('PUI.' + backend)
        if backend == 'wx':
            import wx
            app = wx.GetApp() or wx.App()
        class Demo(ui.Application):
            weight = None
            def content(self):
                with ui.Window(size=(650, 400)):
                    with ui.Grid().layout(weight=1):
                        ui.Label('Tall').layout(width=120, height=180).grid(row=0, column=0)
                        self.button = ui.Button('Connect').layout(weight=self.weight).grid(row=0, column=1)
                        self.field = ui.TextField(ui.DummyBinding('Wide')).grid(row=1, column=1)
        root = Demo()
        retained = None
        try:
            for weight in (None, 1, 0, None):
                root.weight = weight
                root.sync()
                if backend == 'wx':
                    root.children[0].ui.Show()
                    for _ in range(4):
                        app.Yield()
                        app.ProcessPendingEvents()
                    size = lambda n: tuple(n.outer.GetSize())
                    natural = tuple(root.button.ui.GetBestSize())
                else:
                    for _ in range(4): root.ui.update()
                    size = lambda n: (n.outer.winfo_width(), n.outer.winfo_height())
                    natural = (root.button.ui.winfo_reqwidth(), root.button.ui.winfo_reqheight())
                if retained is not None:
                    self.assertIs(root.button.ui, retained)
                retained = root.button.ui
                width, height = size(root.button)
                if weight == 1:
                    self.assertGreater(width, 300)
                    self.assertGreater(height, 180)
                else:
                    self.assertEqual((width, height), natural)
                self.assertGreater(size(root.field)[0], 300)
                self.assertLess(size(root.field)[1], 60)
        finally:
            recur_delete(root, root, True)

    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
