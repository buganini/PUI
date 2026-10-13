"""env/bin/python -m unittest discover -s tests -p tkinter_views.py -v (GUI required)."""
import contextlib
import io
import unittest
import PUI.tkinter as backend
from PUI.dom import recur_delete
from views_native_cases import ViewsNativeCases


class TkViewsTests(ViewsNativeCases, unittest.TestCase):
    backend = backend

    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root:
            recur_delete(self.root, self.root, True)

    def pump(self):
        self.root.ui.update()

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())
        self.pump()

    def mount(self, root):
        self.root = root
        self.sync()

    def selected(self):
        visible = [p._id for p in self.views().children if p.ui.winfo_ismapped()]
        self.assertLessEqual(len(visible), 1)
        return visible[0] if visible else None

    def write_text(self, field, text):
        field.variable.set(text)

    def read_text(self, field):
        return field.variable.get()


if __name__ == '__main__':
    unittest.main()
