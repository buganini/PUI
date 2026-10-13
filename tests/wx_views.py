"""python3 -m unittest discover -s tests -p wx_views.py -v (GUI required)."""
import contextlib
import io
import unittest
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


if __name__ == '__main__':
    unittest.main()
