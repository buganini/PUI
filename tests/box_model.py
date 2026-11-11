"""Native box boundaries: padding is painted inside, margin is outside."""
import importlib
import unittest
from PUI import State
from PUI.dom import recur_delete


class BoxModel(unittest.TestCase):
    def exercise(self, backend):
        ui = importlib.import_module('PUI.' + backend)
        state = State(); state.text = "Text"
        class App(ui.Application):
            inset = 12
            def content(self):
                with ui.Window(size=(500, 400)):
                    with ui.VBox(gap=0).layout(padding=0):
                        with ui.HBox(gap=0).layout(padding=0):
                            with ui.VBox(gap=0).layout(padding=self.inset, margin=(0, 7, 0, 9)).style(bgColor=0x334455) as self.box:
                                self.label = ui.Label('Content').layout(padding=0)
                            self.next = ui.Label('Next').layout(padding=0)
                        with ui.Grid(gap=0).layout(padding=0):
                            self.first = ui.Label('A').layout(margin=(0, 7, 0, 9), padding=0).grid(row=0,column=0)
                            self.second = ui.Label('B').layout(padding=0).grid(row=0,column=1)
                        self.field = ui.TextField(state('text')).layout(width=200, height=60, padding=self.inset)
                        ui.Spacer()
        app = App()
        def rect(node):
            w = node.outer
            if backend == 'PySide6': return w.x(), w.y(), w.width(), w.height()
            if backend == 'wx': return (*w.GetPosition(), *w.GetSize())
            return w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height()
        try:
            original = None
            for inset in (12, 0, 5):
                app.inset = inset
                app.sync()
                for _ in range(5):
                    if backend == 'PySide6': app.ui.processEvents()
                    elif backend == 'wx': app.ui.Yield(); app.ui.ProcessPendingEvents()
                    else: app.ui.update()
                if original is None: original = app.field.ui
                self.assertIs(app.field.ui, original)
                box, label, following = rect(app.box), rect(app.label), rect(app.next)
                self.assertEqual(box[0], 9)
                self.assertEqual(label[0], inset)
                self.assertEqual(label[1], inset)
                self.assertEqual(following[0] - box[0] - box[2], 7)
                a,b=rect(app.first),rect(app.second)
                self.assertEqual(a[0],9)
                self.assertEqual(b[0]-a[0]-a[2],7)
                if backend == 'PySide6':
                    from PySide6.QtWidgets import QStyleOptionFrame
                    option = QStyleOptionFrame()
                    app.field.ui.initStyleOption(option)
                    self.assertEqual(option.rect, app.field.ui.rect())
                    self.assertEqual(app.field.ui.textMargins().left(), inset)
                elif backend == 'tkinter':
                    from tkinter import ttk
                    padding = ttk.Style(app.ui).lookup(app.field.ui.cget('style'), 'padding')
                    self.assertEqual(tuple(map(int, app.ui.tk.splitlist(padding))), (inset,)*4)
        finally:
            recur_delete(app, app, True)

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
