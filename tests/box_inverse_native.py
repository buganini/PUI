"""Native geometry and editor retention for ordinary/adaptive reversed boxes."""
import contextlib
import importlib
import io
import unittest

from PUI.dom import recur_delete


class NativeBoxInverse(unittest.TestCase):
    def exercise(self, backend):
        UI = importlib.import_module('PUI.' + backend)
        if backend == 'PySide6':
            from PySide6.QtWidgets import QApplication, QLineEdit
            native_app = QApplication.instance() or QApplication([])
            type(self)._qt_app = native_app
        elif backend == 'wx':
            import wx
            native_app = wx.GetApp() or wx.App(False)
            type(self)._wx_app = native_app

        for kind in ('HBox', 'VBox', 'HVBox', 'VHBox'):
            with self.subTest(backend=backend, kind=kind):
                class Demo(UI.Application):
                    primary = True
                    inverse = inverse_h = inverse_v = False
                    def setup(self):
                        self.form = UI.State()
                        self.form.a, self.form.b, self.form.c = 'A', 'B', 'C'
                    def content(self):
                        with UI.Window(size=(600, 400)):
                            with UI.VBox().layout(weight=1):
                                cls = getattr(UI, kind)
                                if kind in ('HBox', 'VBox'):
                                    box = cls(inverse=self.inverse)
                                else:
                                    box = cls(1 if self.primary else 10000,
                                              inverseH=self.inverse_h, inverseV=self.inverse_v)
                                with box.layout(weight=1) as self.box:
                                    for name in ('a', 'b', 'c'):
                                        UI.TextField(self.form(name)).id(name)
                root = Demo()
                if backend == 'PySide6':
                    root.ui = native_app
                output = io.StringIO()
                def sync():
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        root.sync()
                    window = root.children[0].ui
                    if backend == 'PySide6':
                        window.show()
                        native_app.processEvents()
                    elif backend == 'wx':
                        window.Show()
                        window.Layout()
                        wx.YieldIfNeeded()
                    else:
                        root.ui.update()
                    self.assertNotIn('<ERROR', output.getvalue())
                try:
                    sync()
                    sync()  # Let native parent measurements settle.
                    original = {c._id: c.ui for c in root.box.children}
                    editor = original['b']
                    if backend == 'PySide6':
                        editor.setText('draft')
                        editor.setFocus()
                        read = editor.text
                    elif backend == 'wx':
                        editor.ChangeValue('draft')
                        editor.SetFocus()
                        read = editor.GetValue
                    else:
                        editor.delete(0, 'end')
                        editor.insert(0, 'draft')
                        editor.focus_force()
                        read = editor.get
                    for primary in (True, False, True):
                        for inverse_h, inverse_v in ((False, False), (True, False),
                                                     (False, True), (True, True)):
                            root.primary = primary
                            root.inverse = inverse_h
                            root.inverse_h, root.inverse_v = inverse_h, inverse_v
                            sync()
                            box = root.box
                            horizontal = kind == 'HBox' if kind in ('HBox', 'VBox') else box.container_x
                            inverse = root.inverse if kind in ('HBox', 'VBox') else (
                                inverse_h if horizontal else inverse_v)
                            fields = {c._id: c.ui for c in box.children}
                            for name, widget in original.items():
                                self.assertIs(fields[name], widget)
                            def coordinate(widget):
                                if backend == 'PySide6':
                                    p = widget.geometry()
                                    return p.x() if horizontal else p.y()
                                if backend == 'wx':
                                    p = widget.GetPosition()
                                    return p.x if horizontal else p.y
                                info = widget.grid_info()
                                return int(info['column' if horizontal else 'row'])
                            positions = [coordinate(fields[name]) for name in ('a', 'b', 'c')]
                            self.assertEqual(positions[0] > positions[2], inverse, positions)
                            self.assertEqual(box.pui_reversed_order, inverse if backend != 'PySide6' else False)
                            self.assertEqual(read(), 'draft')
                finally:
                    if backend == 'PySide6':
                        # Suppress edit commits while deliberately destroying
                        # the test's focused editor and its binding owner.
                        for widget in root.children[0].ui.findChildren(QLineEdit):
                            widget.blockSignals(True)
                    recur_delete(root, root, True)
                    if backend == 'PySide6':
                        native_app.processEvents()
                    elif backend == 'wx':
                        wx.YieldIfNeeded()
                        native_app.ProcessPendingEvents()

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
