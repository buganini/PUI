"""Native Divider expansion, theme thickness and retained adaptive orientation."""
import contextlib
import importlib
import io
import unittest

from PUI.dom import recur_delete


class DividerChecks:
    def setUp(self):
        self.UI = importlib.import_module('PUI.' + self.backend)
        self.root = None
        if self.backend == 'wx':
            import wx
            self.native_app = wx.GetApp() or wx.App(False)
            type(self)._native_app = self.native_app

    def tearDown(self):
        if self.root is not None:
            recur_delete(self.root, self.root, True)
            if self.backend == 'wx':
                import wx
                wx.YieldIfNeeded()
                self.native_app.ProcessPendingEvents()

    def flush(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            for _ in range(3):
                if self.backend == 'wx':
                    import wx
                    self.root.children[0].ui.Layout()
                    wx.YieldIfNeeded()
                    self.native_app.ProcessPendingEvents()
                else:
                    self.root.ui.update()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())
        self.flush()

    def mount(self, content):
        UI = self.UI
        class Demo(UI.Application):
            def content(self):
                with UI.Window(size=(600, 450)):
                    with UI.VBox().layout(weight=1):
                        content()
        self.root = Demo()
        self.sync()
        self.sync()  # Settle the first parent-size observation.

    def size(self, node):
        return tuple(node.ui.GetSize()) if self.backend == 'wx' else (
            node.ui.winfo_width(), node.ui.winfo_height())

    def check_line(self, box, divider):
        vertical = getattr(box, 'container_x', isinstance(box, self.UI.HBox))
        width, height = self.size(box)
        line_width, line_height = self.size(divider)
        if self.backend == 'wx':
            self.assertEqual(divider.ui.IsVertical(), vertical)
            thickness = divider.ui.GetDefaultSize()
            self.assertTrue(divider.ui.IsShownOnScreen())
        else:
            self.assertEqual(str(divider.ui.cget('orient')), 'vertical' if vertical else 'horizontal')
            thickness = divider.ui.winfo_reqwidth() if vertical else divider.ui.winfo_reqheight()
            self.assertTrue(divider.ui.winfo_ismapped())
        self.assertEqual(line_width if vertical else line_height, thickness)
        self.assertEqual(line_height if vertical else line_width, height if vertical else width)
        self.assertGreater(line_height if vertical else line_width, 100)

    def test_linear_expansion_through_virtual_view_and_resize(self):
        UI = self.UI
        class Nested(UI.PUIView):
            def content(view):
                UI.Divider().id('line').layout(padding=0)
        for kind in ('HBox', 'VBox'):
            with self.subTest(kind=kind):
                def content():
                    with getattr(UI, kind)().layout(weight=1, padding=0):
                        UI.Label('Before')
                        Nested()
                        UI.Label('After')
                        UI.Spacer()
                self.mount(content)
                for width, height in ((600, 450), (820, 560), (420, 320)):
                    window = self.root.children[0].ui
                    if self.backend == 'wx':
                        window.SetClientSize((width, height))
                    else:
                        window.geometry(f'{width}x{height}')
                    self.flush()
                    box = self.root.children[0].children[0].children[0]
                    self.check_line(box, box.children[1].children[0])
                self.tearDown()
                self.root = None

    def test_adaptive_orientation_retains_native_separator(self):
        UI = self.UI
        primary = True
        for kind in ('HVBox', 'VHBox'):
            with self.subTest(kind=kind):
                def content():
                    with getattr(UI, kind)(1 if primary else 10000).layout(weight=1, padding=0):
                        UI.Label('Before')
                        UI.Divider().layout(padding=0)
                        UI.Label('After')
                        UI.Spacer()
                self.mount(content)
                original = self.root.children[0].children[0].children[0].children[1].ui
                for primary in (True, False, True, False):
                    self.sync()
                    box = self.root.children[0].children[0].children[0]
                    line = box.children[1]
                    self.assertIs(line.ui, original)
                    self.check_line(box, line)
                self.tearDown()
                self.root = None


class WxDividerTests(DividerChecks, unittest.TestCase):
    backend = 'wx'


class TkDividerTests(DividerChecks, unittest.TestCase):
    backend = 'tkinter'

    def test_available_themes(self):
        from tkinter import ttk
        UI = self.UI
        def content():
            for kind in ('HBox', 'VBox'):
                with getattr(UI, kind)().layout(weight=1, padding=0):
                    UI.Label('Before')
                    UI.Divider().layout(padding=0)
                    UI.Spacer()
        self.mount(content)
        style = ttk.Style(self.root.ui)
        for theme in style.theme_names():
            with self.subTest(theme=theme):
                style.theme_use(theme)
                self.flush()
                for box in self.root.children[0].children[0].children:
                    self.check_line(box, box.children[1])
