"""python3 -m unittest discover -s tests -p wx_splitter.py -v (GUI required)."""
import contextlib
import io
import unittest

import wx
from PUI.wx import Application, PUIView, Window, Splitter, VBox, Label, TextField, DummyBinding
from PUI.dom import recur_delete


class WxSplitterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()

    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root is not None and not self.root.destroyed:
            recur_delete(self.root, self.root, True)
        for window in wx.GetTopLevelWindows():
            window.Destroy()
        self.pump()

    def pump(self):
        for _ in range(4):
            wx.MilliSleep(10)
            self.app.Yield()
            self.app.ProcessPendingEvents()

    def sync(self, view=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            (view or self.root).sync()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())
        self.pump()

    def mount(self, root):
        self.root = root
        self.sync()
        root.children[0].ui.Show()
        self.pump()
        return root.children[0].children[0]

    def test_three_panes_nest_on_right_and_layout_children_have_native_parent(self):
        class Example(Application):
            def content(self):
                with Window(size=(900, 400)):
                    with Splitter():
                        with VBox():
                            Label('first')
                            Label('second')
                        Label('middle')
                        Label('right')
        splitter = self.mount(Example())
        host = splitter.ui
        self.assertEqual(len(host.splitters), 2)
        self.assertIs(host.splitters[0].GetWindow1(), host.panes[0])
        self.assertIs(host.splitters[0].GetWindow2(), host.splitters[1])
        self.assertIs(host.splitters[1].GetWindow1(), host.panes[1])
        self.assertIs(host.splitters[1].GetWindow2(), host.panes[2])
        for label in splitter.children[0].children:
            self.assertIs(label.ui.GetParent(), host.panes[0])
        widths = [pane.GetSize().width for pane in host.panes]
        self.assertGreater(min(widths), 200)
        self.assertLess(max(widths) - min(widths), 15)
        x = [pane.GetScreenPosition().x for pane in host.panes]
        self.assertLess(x[0], x[1])
        self.assertLess(x[1], x[2])

    def test_redraw_retains_sashes_and_resize_shares_space(self):
        class Example(Application):
            text = 'a'
            def content(self):
                with Window(size=(900, 400)):
                    with Splitter():
                        Label(self.text).id('a')
                        Label('b').id('b')
                        Label('c').id('c')
        root = Example()
        splitter = self.mount(root)
        native = list(splitter.ui.splitters)
        native[0].SetSashPosition(220)
        native[1].SetSashPosition(260)
        self.pump()
        positions = [s.GetSashPosition() for s in native]
        root.text = 'updated'
        self.sync()
        splitter = root.children[0].children[0]
        self.assertEqual(splitter.ui.splitters, native)
        self.assertEqual([s.GetSashPosition() for s in native], positions)
        self.assertEqual(splitter.children[0].ui.GetLabel(), 'updated')
        widths = [p.GetSize().width for p in splitter.ui.panes]
        root.children[0].ui.SetSize((1200, 400))
        self.pump()
        gains = [p.GetSize().width - old for p, old in zip(splitter.ui.panes, widths)]
        self.assertTrue(all(90 <= gain <= 110 for gain in gains), gains)

    def test_keyed_reorder_and_removal_preserve_widgets_and_drafts(self):
        models = {key: DummyBinding(key) for key in 'abcd'}
        class Example(Application):
            order = list('abc')
            def content(self):
                with Window(size=(900, 400)):
                    with Splitter():
                        for key in self.order:
                            with VBox().id(key):
                                TextField(models[key])
        root = Example()
        splitter = self.mount(root)
        widgets = {c._id: c.children[0].ui for c in splitter.children}
        widgets['c'].ChangeValue('uncommitted')
        root.order = list('cad')
        self.sync()
        splitter = root.children[0].children[0]
        self.assertEqual([p.child._id for p in splitter.ui.panes], list('cad'))
        for pane in splitter.ui.panes:
            key = pane.child._id
            field = pane.child.children[0].ui
            self.assertIs(field.GetParent(), pane)
            if key in widgets:
                self.assertIs(field, widgets[key])
        self.assertEqual(widgets['c'].GetValue(), 'uncommitted')
        self.assertFalse(bool(widgets['b']))

    def test_empty_single_and_multiple_panes(self):
        class Example(Application):
            order = []
            def content(self):
                with Window(size=(800, 400)):
                    with Splitter():
                        for key in self.order:
                            Label(key).id(key)
        root = Example()
        self.mount(root)
        for order in ('a', 'ab', 'abc', 'b', '', 'cd', ''):
            with self.subTest(order=order):
                root.order = list(order)
                self.sync()
                host = root.children[0].children[0].ui
                self.assertEqual(len(host.panes), len(order))
                self.assertEqual(len(host.splitters), max(0, len(order) - 1))
                self.assertTrue(all(p.IsShownOnScreen() for p in host.panes))

    def test_orientation_change_keeps_controls_and_nests_at_bottom(self):
        class Example(Application):
            vertical = False
            def content(self):
                with Window(size=(700, 700)):
                    with Splitter(vertical=self.vertical):
                        Label('a').id('a')
                        Label('b').id('b')
                        Label('c').id('c')
        root = Example()
        splitter = self.mount(root)
        widgets = [n.ui for n in splitter.children]
        root.vertical = True
        self.sync()
        splitter = root.children[0].children[0]
        self.assertEqual([n.ui for n in splitter.children], widgets)
        self.assertTrue(all(s.GetSplitMode() == wx.SPLIT_HORIZONTAL for s in splitter.ui.splitters))
        y = [p.GetScreenPosition().y for p in splitter.ui.panes]
        self.assertLess(y[0], y[1])
        self.assertLess(y[1], y[2])

    def test_explicit_nesting_padding_and_layout_replacement(self):
        class Example(Application):
            layout = True
            padding = (2, 4, 6, 8)
            def content(self):
                with Window(size=(800, 600)):
                    with Splitter(vertical=True):
                        with Splitter():
                            if self.layout:
                                with VBox().layout(padding=self.padding):
                                    Label('a')
                            else:
                                Label('replacement')
                            Label('b')
                        Label('bottom')
        root = Example()
        outer = self.mount(root)
        inner = outer.children[0]
        self.assertIs(inner.ui.GetParent(), outer.ui.panes[0])
        pane = inner.ui.panes[0]
        self.assertEqual([tuple(i.GetMinSize()) for i in pane.padding], [(0, 2), (4, 0), (0, 6), (8, 0)])
        old = inner.children[0].children[0].ui
        root.layout = False
        self.sync()
        inner = root.children[0].children[0].children[0]
        self.assertFalse(bool(old))
        self.assertEqual(inner.children[0].ui.GetLabel(), 'replacement')
        self.assertIs(inner.children[0].ui.GetParent(), inner.ui.panes[0])

    def test_independent_subview_updates_native_panes_and_padding(self):
        class Panes(PUIView):
            order = list('ab')
            pad = 3
            def content(self):
                for key in self.order:
                    Label(key).id(key).layout(padding=self.pad)
        class Example(Application):
            def content(self):
                with Window(size=(800, 400)):
                    with Splitter():
                        Panes()
        splitter = self.mount(Example())
        view = splitter.children[0]
        for order in ('cab', 'c', '', 'ab'):
            view.order = list(order)
            view.pad = 9
            self.sync(view)
            self.assertEqual([p.child._id for p in splitter.ui.panes], list(order))
            self.assertTrue(all(tuple(p.padding[0].GetMinSize()) == (0, 9) for p in splitter.ui.panes))
        view.pad = 4
        self.sync(view)
        self.assertTrue(all(tuple(p.padding[0].GetMinSize()) == (0, 4) for p in splitter.ui.panes))


if __name__ == '__main__':
    unittest.main()
