import importlib
import unittest
from PUI.gap import gap_value
from PUI.dom import recur_delete


class GapValidation(unittest.TestCase):
    def test_values(self):
        self.assertEqual(gap_value(0, pair=True), (0, 0))
        self.assertEqual(gap_value((2, 5), pair=True, terminal=True), (2, 5))
        for value in (-1, float('nan'), float('inf'), True, '8'):
            with self.assertRaises(ValueError): gap_value(value)
        with self.assertRaises(ValueError): gap_value((1, 2, 3), pair=True)
        with self.assertRaises(ValueError): gap_value(.5, terminal=True)


class NativeGaps(unittest.TestCase):
    def exercise(self, backend):
        ui = importlib.import_module('PUI.' + backend)
        class App(ui.Application):
            gap = 12
            hidden = True
            inverse = False
            def content(self):
                with ui.Window(size=(500, 350)):
                    with ui.VBox(gap=7).layout(padding=0):
                        with ui.HBox(gap=self.gap, inverse=self.inverse).layout(padding=0) as self.box:
                            self.a = ui.Label('A').layout(width=40, height=30, padding=0)
                            ui.Label('Hidden').visible(not self.hidden).layout(width=40, height=30, padding=0)
                            self.b = ui.Label('B').layout(width=40, height=30, padding=0)
                        with ui.Grid(gap=(self.gap, self.gap+3)).layout(padding=0) as self.grid:
                            self.c = ui.Label('C').grid(row=0,column=0).layout(width=40,height=30,padding=0)
                            self.d = ui.Label('D').grid(row=0,column=1).layout(width=40,height=30,padding=0)
                            self.e = ui.Label('Span').grid(row=1,column=0,columnspan=2).layout(width=80,height=30,padding=0)
                        ui.Spacer()
        app = App()
        def rect(node):
            w = node.outer
            if backend == 'PySide6': return w.x(), w.y(), w.width(), w.height()
            if backend == 'wx': return (*w.GetPosition(), *w.GetSize())
            return w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height()
        try:
            for gap, inverse in ((12,False),(0,False),(9,True)):
                app.gap, app.inverse = gap, inverse
                app.sync()
                if backend == 'PySide6':
                    for _ in range(4): app.ui.processEvents()
                elif backend == 'wx':
                    for _ in range(4): app.ui.Yield(); app.ui.ProcessPendingEvents()
                else:
                    for _ in range(4): app.ui.update()
                a,b=sorted((rect(app.a),rect(app.b)))
                self.assertEqual(b[0]-(a[0]+a[2]),gap)
                c,d,e=rect(app.c),rect(app.d),rect(app.e)
                self.assertEqual(d[0]-(c[0]+c[2]),gap+3)
                self.assertEqual(e[1]-(c[1]+c[3]),gap)
        finally:
            recur_delete(app,app,True)

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
