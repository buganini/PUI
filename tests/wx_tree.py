"""python3 -m unittest discover -s tests -p wx_tree.py -v (GUI required)."""
import contextlib
import io
import unittest
import wx
import wx.dataview as dv
from PUI.wx import Application, Window, Tree, TreeNode, BaseTreeAdapter
from PUI.dom import recur_delete


class WxTreeTests(unittest.TestCase):
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
            # GTK's frame clock lays out expanded rows on the next frame.
            wx.MilliSleep(10)
            self.app.Yield()
            self.app.ProcessPendingEvents()

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())
        self.pump()

    def mount(self, root):
        self.root = root
        self.sync()
        root.children[0].ui.Show()
        self.pump()
        return root.children[0].children[0]

    def item(self, tree, text):
        return next(dv.DataViewItem(identity) for identity, entry in tree.wx_model.entries.items()
                    if identity and entry.text == text)

    def test_keyed_reorder_retains_native_selection_expansion_and_current_callbacks(self):
        calls = []
        class Example(Application):
            rows = ['a', 'b']
            version = 0
            def content(self):
                with Window(size=(600, 400)):
                    with Tree():
                        for label in self.rows:
                            with TreeNode(label).id(label).expand(calls.append, ('expand', self.version)):
                                TreeNode(label + '-child').click(lambda e, v=self.version: calls.append(v))
        tree = self.mount(Example())
        ui, model = tree.ui, tree.wx_model
        a, child = self.item(tree, 'a'), self.item(tree, 'a-child')
        ui.Expand(a)
        ui.Select(child)
        self.assertIn(('expand', 0), calls)
        calls.clear()
        self.root.rows.reverse()
        self.root.version = 1
        self.sync()
        tree = tree.get_node()
        self.assertIs(tree.ui, ui)
        self.assertEqual(self.item(tree, 'a'), a)
        self.assertEqual(ui.GetSelection(), child)
        self.assertTrue(ui.IsExpanded(a))
        self.assertLess(ui.GetItemRect(self.item(tree, 'b')).y, ui.GetItemRect(a).y)
        self.assertEqual(calls, [])
        tree.dispatch(child, 'clicked')
        ui.Collapse(a)
        ui.Expand(a)
        self.assertEqual(calls, [1, ('expand', 1)])

        self.root.rows = ['b']
        self.sync()
        tree.dispatch(child, 'clicked')
        self.assertNotIn(int(child.GetID()), model.entries)
        self.assertEqual(calls, [1, ('expand', 1)])

    def test_native_mouse_hit_testing(self):
        calls = []
        class Example(Application):
            def content(self):
                with Window(size=(600, 400)):
                    with Tree():
                        TreeNode('target').click(lambda e: calls.append('click')).dblclick(
                            lambda e: calls.append('double'))
        tree = self.mount(Example())
        rect = tree.ui.GetItemRect(self.item(tree, 'target'))
        for event_type in (wx.wxEVT_LEFT_UP, wx.wxEVT_LEFT_DCLICK):
            event = wx.MouseEvent(event_type)
            event.SetPosition(wx.Point(rect.x + 30, rect.y + rect.height // 2))
            tree.ui.GetEventHandler().ProcessEvent(event)
        self.assertEqual(calls, ['click', 'double'])

    def test_label_single_selects_double_toggles_once(self):
        class Example(Application):
            def content(self):
                with Window(size=(600,400)):
                    with Tree():
                        with TreeNode('parent'):
                            TreeNode('child')
        tree = self.mount(Example())
        item = self.item(tree, 'parent')
        rect = tree.ui.GetItemRect(item)
        def mouse(kind):
            event = wx.MouseEvent(kind)
            event.SetPosition(wx.Point(rect.x+30, rect.y+rect.height//2))
            tree.ui.GetEventHandler().ProcessEvent(event)
            self.pump()
        mouse(wx.wxEVT_LEFT_UP)
        self.assertFalse(tree.ui.IsExpanded(item))
        mouse(wx.wxEVT_LEFT_DCLICK)
        mouse(wx.wxEVT_LEFT_UP)
        self.assertTrue(tree.ui.IsExpanded(item))
        mouse(wx.wxEVT_LEFT_DCLICK)
        mouse(wx.wxEVT_LEFT_UP)
        self.assertFalse(tree.ui.IsExpanded(item))
        tree.expandable(False)
        mouse(wx.wxEVT_LEFT_DCLICK)
        self.assertFalse(tree.ui.IsExpanded(item))

    def test_leaf_container_transitions_empty_and_stale_tree(self):
        class Example(Application):
            extra = []
            show = True
            def content(self):
                with Window(size=(500, 300)):
                    if self.show:
                        with Tree():
                            with TreeNode('parent'):
                                for label in self.extra:
                                    TreeNode(label).id(label)
        tree = self.mount(Example())
        parent = self.item(tree, 'parent')
        tree.ui.Select(parent)
        self.assertFalse(tree.wx_model.IsContainer(parent))
        self.root.extra = ['new']
        self.sync()
        tree = tree.get_node()
        self.assertTrue(tree.wx_model.IsContainer(parent))
        self.assertEqual(tree.ui.GetSelection(), parent)
        tree.expandAll()
        self.pump()
        self.assertTrue(tree.ui.IsExpanded(parent))
        self.assertFalse(tree.ui.GetItemRect(self.item(tree, 'new')).IsEmpty())
        self.root.extra = []
        self.sync()
        tree = tree.get_node()
        self.assertFalse(tree.wx_model.IsContainer(parent))
        self.root.show = False
        self.sync()
        tree.dispatch(parent, 'clicked')
        tree.expandAll().collapseAll().expandable(False)

    def test_adapter_structure_reparent_relabel_and_events(self):
        calls = []
        class Node:
            def __init__(self, text, *children):
                self.text, self.children = text, list(children)
        leaf = Node('leaf')
        left, right = Node('left', leaf), Node('right', Node('other'))
        class Adapter(BaseTreeAdapter):
            roots = [left, right]
            def rowCount(self, parent):
                return len(parent.children if parent else self.roots)
            def child(self, parent, index):
                return (parent.children if parent else self.roots)[index]
            def data(self, node):
                return node.text
            def clicked(self, node):
                calls.append(('click', node))
            def dblclicked(self, node):
                calls.append(('double', node))
            def expanded(self, node):
                calls.append(('expand', node))
        adapter = Adapter()
        class Example(Application):
            def content(self):
                with Window(size=(600, 400)):
                    Tree(adapter)
        tree = self.mount(Example())
        item = self.item(tree, 'leaf')
        tree.expandAll()
        tree.ui.Select(item)
        left.children.remove(leaf)
        right.children.append(leaf)
        leaf.text = 'changed'
        self.sync()
        tree = tree.get_node()
        self.assertEqual(self.item(tree, 'changed'), item)
        self.assertEqual(tree.wx_model.GetParent(item), self.item(tree, 'right'))
        self.assertEqual(tree.ui.GetSelection(), item)
        calls.clear()
        tree.dispatch(item, 'clicked')
        tree.dispatch(item, 'dblclicked')
        self.assertEqual(calls, [('click', leaf), ('double', leaf)])
        adapter.roots = []
        self.sync()
        tree.dispatch(item, 'clicked')
        self.assertEqual(len(tree.wx_model.entries), 1)
        adapter.roots = [right]
        self.sync()
        self.assertEqual(len(tree.wx_model.entries), 4)

    def test_pending_actions_and_expansion_veto(self):
        class Example(Application):
            def content(self):
                with Window(size=(600, 400)):
                    with Tree().expandAll().expandable(False):
                        with TreeNode('a'):
                            with TreeNode('b'):
                                TreeNode('c')
        tree = self.mount(Example())
        a, b = self.item(tree, 'a'), self.item(tree, 'b')
        self.assertTrue(tree.ui.IsExpanded(a))
        self.assertTrue(tree.ui.IsExpanded(b))
        tree.ui.Collapse(a)
        self.assertTrue(tree.ui.IsExpanded(a))
        tree.collapseAll()
        self.assertFalse(tree.ui.IsExpanded(a))
        self.assertFalse(tree.ui.IsExpanded(b))
        tree.expandAll()
        self.assertTrue(tree.ui.IsExpanded(a))
        tree.expandable(True)
        tree.ui.Collapse(a)
        self.assertFalse(tree.ui.IsExpanded(a))


if __name__ == '__main__':
    unittest.main()
