"""Shared browser Tree protocol and retained state tests."""
import asyncio
import unittest
from PUI.web import Application, Window, Tree, TreeNode
from PUI.web.runtime import Runtime
from PUI._browser.messages import validate_client_body
from PUI._browser.schema import ProtocolError


class Example(Application):
    order = ['a', 'b']
    version = 0
    def setup(self):
        self.calls = []
    def content(self):
        with Window():
            with Tree():
                for text in self.order:
                    with TreeNode(text).id(text).expand(self.calls.append, ('open', text)):
                        TreeNode(text+' child').click(lambda e,v=self.version: self.calls.append(v))


class BrowserTreeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = Example()
        self.refresh()

    async def asyncTearDown(self):
        self.runtime.close()

    def refresh(self):
        self.runtime.app.sync(); self.runtime.flush()
        return self.runtime.snapshot()

    def tree(self):
        return self.runtime.app.children[0].children[0]

    def event(self, item, action):
        tree = self.tree()
        return dict(node_id=tree.ui.id,event='tree',token=tree.ui.events['tree'],observed_render_rev=1,
                    data=dict(item=item,action=action))

    def test_snapshot_events_reorder_delete_and_commands(self):
        tree = self.tree()
        rows = tree.properties()['nodes']
        a, child = rows[0]['id'], rows[1]['id']
        self.assertEqual(tree.ui.children, [])
        self.assertEqual(self.runtime.action('event',self.event(a,'expanded'))[0], 'processed')
        self.assertEqual(self.runtime.app.calls, [('open','a')])
        self.assertEqual(self.runtime.action('event',self.event(child,'clicked'))[0], 'processed')
        self.assertEqual(self.runtime.app.calls[-1],0)
        old = tree.properties()
        self.runtime.app.order = ['b','a']; self.runtime.app.version = 1
        self.refresh()
        tree = self.tree()
        self.assertEqual(tree.tree_state.selected,child)
        self.assertIn(a,tree.tree_state.expanded)
        self.assertEqual(tree.properties()['nodes'][2]['id'],a)
        self.assertEqual(old['nodes'][0]['id'],a)  # published records stay immutable
        self.runtime.action('event',self.event(child,'clicked'))
        self.assertEqual(self.runtime.app.calls[-1],1)
        tree.expandable(False)
        self.assertEqual(self.runtime.action('event',self.event(a,'collapsed'))[0],'stale')
        tree.collapseAll(); self.assertFalse(tree.tree_state.expanded)
        tree.expandAll(); self.assertEqual(len(tree.tree_state.expanded),2)
        self.runtime.app.order=['b']; self.refresh()
        self.assertEqual(self.runtime.action('event',self.event(child,'clicked'))[0],'stale')
        self.assertIsNone(self.tree().tree_state.selected)

    def test_event_validation(self):
        for item,action in ((True,'clicked'),(0,'clicked'),(1,'toggle'),('1','clicked')):
            with self.assertRaises(ProtocolError):
                validate_client_body('event',self.event(item,action))
        body=self.event(1,'expanded');body['token']='old'
        self.assertEqual(self.runtime.action('event',body)[0],'stale')

    def test_pyodide_uses_the_same_renderer_contract(self):
        from PUI.pyodide import Tree as PyTree, TreeNode as PyNode
        self.assertIs(PyTree,Tree)
        self.assertIs(PyNode,TreeNode)
