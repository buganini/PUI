"""Run with python3 -m unittest discover -s tests -p wx_regression.py (GUI required)."""
import contextlib
import io
import unittest
from unittest.mock import patch

import wx
from PUI.wx import Application, PUI, PUIView, Window, VBox, Label, Button
from PUI.dom import recur_delete


class WxRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()

    def tearDown(self):
        for view in list(PUIView.__ALLVIEWS__):
            if isinstance(view, PUIView) and not view.destroyed:
                recur_delete(view, view, True)
        for window in wx.GetTopLevelWindows():
            window.Destroy()
        self.pump()

    def pump(self):
        for _ in range(4):
            self.app.Yield()
            self.app.ProcessPendingEvents()

    def sync(self, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            root.sync()
        self.assertNotIn('<ERROR', output.getvalue())

    def test_redraw_coalesces_and_destroyed_queue_is_safe(self):
        view = PUIView()
        queued = []
        with patch('wx.CallAfter', side_effect=lambda cb: queued.append(cb)):
            for _ in range(1000):
                view.redraw()
        self.assertEqual(len(queued), 1)
        self.assertTrue(view.updating)
        recur_delete(view, view, True)
        queued.pop()()
        self.assertFalse(view.updating)

    def test_decorator_uses_wx_view(self):
        @PUI
        def Child():
            Label('child')
        self.assertIsInstance(Child(), PUIView)

    def test_keyed_reorder_reuses_widgets_and_updates_callbacks(self):
        calls = []
        class Example(Application):
            order = ['a', 'b', 'c']
            generation = 0
            def content(self):
                with Window(size=(320, 240)):
                    with VBox():
                        for key in self.order:
                            Button(key).id(key).click(lambda e, value: calls.append(value), self.generation)
        root = Example()
        self.sync(root)
        box = root.children[0].children[0]
        widgets = {n._id: n.ui for n in box.children}
        self.assertIs(widgets['a'].GetParent(), root.children[0].panel)
        root.order = ['c', 'a']
        root.generation = 1
        self.sync(root)
        box = root.children[0].children[0]
        self.assertEqual([n._id for n in box.children], ['c', 'a'])
        for node in box.children:
            self.assertIs(node.ui, widgets[node._id])
            node._clicked()
        self.assertEqual(calls, [1, 1])
        self.pump()
        self.assertFalse(bool(widgets['b']))

    def test_replace_window_content_and_remove_layout_subtree(self):
        class Example(Application):
            show_layout = True
            def content(self):
                with Window(size=(320, 240)):
                    if self.show_layout:
                        with VBox():
                            Label('inside')
                    else:
                        Label('direct')
        root = Example()
        self.sync(root)
        old = root.children[0].children[0].children[0].ui
        root.show_layout = False
        self.sync(root)
        self.pump()
        window = root.children[0]
        self.assertFalse(bool(old))
        self.assertIs(window.children[0].ui.GetParent(), window.panel)
        self.assertEqual(window.panel.GetSizer().GetItemCount(), 1)

    def test_nested_view_updates_on_gui_queue(self):
        @PUI
        def Child():
            Label('nested')
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        Child()
        root = Example()
        self.sync(root)
        child = root.children[0].children[0].children[0]
        label = child.children[0].ui
        child.redraw()
        self.pump()
        self.assertIs(child.children[0].ui, label)
        self.assertFalse(child.updating)


if __name__ == '__main__':
    unittest.main()
