"""Native Tk panes: geometry, sash retention, reordering and orientation changes."""
import contextlib
import io
import unittest
import PUI.tkinter as UI
from PUI.dom import recur_delete


class TkSplitter(unittest.TestCase):
    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root is not None:
            recur_delete(self.root, self.root, True)

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
            self.root.ui.update()
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())

    def test_native_panes_preserve_sash_and_editor_then_reorder(self):
        model = UI.DummyBinding('initial')
        class Demo(UI.Application):
            order = ['a', 'b', 'c']
            vertical = False
            hidden = False
            def content(self):
                with UI.Window(size=(900, 600)):
                    with UI.Splitter(vertical=self.vertical) as self.split:
                        for key in self.order:
                            with UI.VBox().id(key).visible(not(self.hidden and key == 'b')):
                                UI.TextField(model)
        self.root = Demo()
        self.sync()
        split = self.root.split
        host = split.ui
        self.assertEqual(len(host.paned.panes()), 3)
        host.paned.sashpos(0, 180)
        self.root.ui.update()
        position = host.paned.sashpos(0)
        sash_x = next(x for x in range(max(0, position - 10), position + 20)
                      if host.paned.identify(x, 50) == 0)
        host.paned.event_generate('<ButtonPress-1>', x=sash_x, y=50)
        host.paned.event_generate('<B1-Motion>', x=sash_x + 40, y=50)
        host.paned.event_generate('<ButtonRelease-1>', x=sash_x + 40, y=50)
        self.root.ui.update()
        self.assertGreater(host.paned.sashpos(0), position + 30)
        position = host.paned.sashpos(0)
        editor = split.children[0].children[0]
        editor.variable.set('draft')
        widget = editor.ui
        self.assertIs(widget.winfo_containing(widget.winfo_rootx() + 5, widget.winfo_rooty() + 5), widget)
        self.sync()
        self.assertIs(self.root.split.ui, host)
        self.assertEqual(host.paned.sashpos(0), position)
        self.assertIs(self.root.split.children[0].children[0].ui, widget)
        self.assertEqual(widget.get(), 'draft')
        self.root.order = ['c', 'a', 'd']
        self.sync()
        self.assertIs(self.root.split.children[1].children[0].ui, widget)
        self.root.vertical = True
        self.sync()
        self.assertEqual(str(host.paned.cget('orient')), 'vertical')
        self.assertIs(self.root.split.children[1].children[0].ui, widget)
        frames = [host.frames[node.outer] for node in self.root.split.children]
        self.assertLess(frames[0].winfo_y(), frames[1].winfo_y())
        self.assertLess(frames[1].winfo_y(), frames[2].winfo_y())
        for order in (['a'], [], ['a', 'b', 'c']):
            self.root.order = order
            self.sync()
            self.assertEqual(len(host.paned.panes()), len(order))
        self.root.hidden = True
        self.sync()
        self.assertEqual(len(host.paned.panes()), 2)

    def test_independent_view_updates_panes(self):
        class Panes(UI.PUIView):
            order = ['a', 'b']
            def content(self):
                for key in self.order:
                    UI.Label(key).id(key)
        class Demo(UI.Application):
            def content(self):
                with UI.Window(size=(700, 400)):
                    with UI.Splitter() as self.split:
                        Panes()
        self.root = Demo()
        self.sync()
        view = self.root.split.children[0]
        for order in (['c', 'a', 'b'], [], ['a']):
            view.order = order
            view.sync()
            self.root.ui.update()
            self.assertEqual(len(self.root.split.ui.paned.panes()), len(order))


if __name__ == '__main__':
    unittest.main()
