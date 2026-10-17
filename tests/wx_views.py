"""python3 -m unittest discover -s tests -p wx_views.py -v (GUI required)."""
import contextlib
import io
import sys
import unittest
from unittest.mock import patch
import wx
import PUI.wx as backend
from PUI.dom import recur_delete
from views_native_cases import ViewsNativeCases


class WxViewsTests(ViewsNativeCases, unittest.TestCase):
    backend = backend

    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()

    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root:
            recur_delete(self.root, self.root, True)
        for window in wx.GetTopLevelWindows():
            window.Destroy()
        self.pump()

    def pump(self):
        for _ in range(4):
            wx.MilliSleep(10)
            self.app.Yield()
            self.app.ProcessPendingEvents()

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())
        self.pump()

    def mount(self, root):
        self.root = root
        self.sync()
        self.root.children[0].ui.Show()
        self.pump()

    def selected(self):
        views = self.views()
        index = views.ui.GetSelection()
        for i, page in enumerate(views.children):
            self.assertEqual(page.ui.IsShownOnScreen(), i + 1 == index)
        return views.children[index - 1]._id if index > 0 else None

    def write_text(self, field, text):
        field.ui.ChangeValue(text)

    def read_text(self, field):
        return field.ui.GetValue()

    def test_switch_between_table_and_views_cookbook(self):
        with patch.object(sys, 'argv', ['cookbook', 'wx']):
            from PUI.cookbook.table import TableExample
            from PUI.cookbook.views import ViewsExample

        class Example(backend.Application):
            example_type = TableExample

            def content(self):
                with backend.Window(size=(700, 700)):
                    with backend.VBox():
                        backend.Label('Result')
                        if self.example_type is not None:
                            self.example = self.example_type()

        def windows(node):
            result = [node.ui] if isinstance(node.ui, wx.Window) else []
            for child in node.children:
                result.extend(windows(child))
            return result

        self.mount(Example())
        result_label = self.root.children[0].children[0].children[0].ui
        for example_type in (ViewsExample, TableExample, ViewsExample, None):
            with self.subTest(example=example_type):
                previous = self.root.example
                old_windows = windows(previous)
                self.assertTrue(old_windows)
                self.root.example_type = example_type
                self.sync()
                self.assertTrue(previous.destroyed)
                self.assertTrue(all(not window for window in old_windows),
                                'Removed example left native controls alive')
                self.assertTrue(result_label.IsShownOnScreen())
                if example_type is not None:
                    self.assertTrue(any(window.IsShownOnScreen()
                                        for window in windows(self.root.example)))


if __name__ == '__main__':
    unittest.main()
