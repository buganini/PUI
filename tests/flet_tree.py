"""Run with: env/bin/python -m unittest discover -s tests -p flet_tree.py -v"""
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from PUI.flet import Application, Window, Tree, TreeNode, BaseTreeAdapter
import flet_regression


class FletTreeTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = flet_regression.FletRegression.asyncSetUp
    asyncTearDown = flet_regression.FletRegression.asyncTearDown
    mount = flet_regression.FletRegression.mount
    sync = flet_regression.FletRegression.sync
    flush_callbacks = flet_regression.FletRegression.flush_callbacks

    def tree(self):
        return self.root.children[0].children[0]

    def key(self, text):
        return next(k for k, e in self.tree().tree_state.entries.items() if e.text == text)

    async def test_declarations_events_reorder_and_commands(self):
        calls = []
        class Example(Application):
            order = ['a', 'b']
            version = 0
            def content(self):
                with Window():
                    with Tree():
                        for name in self.order:
                            with TreeNode(name).id(name).expand(calls.append, 'expanded'):
                                TreeNode(name+' child').click(lambda e, v=self.version: calls.append(('click', v)))
        await self.mount(Example())
        tree = self.tree()
        tree.ui.focus = AsyncMock()
        a = self.key('a')
        label = tree.rows[a].content.controls[1]
        await self.session.dispatch_event(label._i, 'tap', {})
        await self.flush_callbacks()
        self.assertNotIn(a, tree.tree_state.expanded)
        await self.session.dispatch_event(label._i, 'double_tap', None)
        await self.flush_callbacks()
        self.assertIn(a, tree.tree_state.expanded)
        await self.session.dispatch_event(label._i, 'double_tap', None)
        await self.flush_callbacks()
        self.assertNotIn(a, tree.tree_state.expanded)
        calls.clear()
        arrow = tree.rows[a].content.controls[0]
        await self.session.dispatch_event(arrow._i, 'click', None)
        await self.flush_callbacks()
        self.assertIn(a, tree.tree_state.expanded)
        self.assertEqual(calls, ['expanded'])
        child = self.key('a child')
        hit = tree.rows[child].content.controls[1]
        await self.session.dispatch_event(hit._i, 'tap', {})
        await self.flush_callbacks()
        self.assertEqual(calls[-1], ('click', 0))
        self.assertEqual(tree.tree_state.selected, child)
        row = tree.rows[a]
        self.root.order.reverse()
        self.root.version = 1
        self.sync()
        tree = self.tree()
        self.assertIs(tree.rows[a], row)
        self.assertEqual(tree.tree_state.selected, child)
        self.assertIn(a, tree.tree_state.expanded)
        await self.session.dispatch_event(hit._i, 'tap', {})
        await self.flush_callbacks()
        self.assertEqual(calls[-1], ('click', 1))
        tree.collapseAll()
        await self.flush_callbacks()
        self.assertFalse(tree.tree_state.expanded)
        tree.expandable(False)
        await self.flush_callbacks()
        await self.session.dispatch_event(tree.ui._i, 'key_down', {'key': 'Home'})
        await tree._key(SimpleNamespace(key='Arrow Right'))
        self.assertFalse(tree.tree_state.expanded)
        for opened in (False, True, False):
            (tree.expandAll if opened else tree.collapseAll)()
            await self.flush_callbacks()
            arrow, label = tree.rows[a].content.controls
            self.assertTrue(arrow.disabled)
            for control, event in ((arrow, 'click'), (label, 'tap'), (label, 'double_tap')):
                await self.session.dispatch_event(control._i, event, {} if event == 'tap' else None)
                await self.flush_callbacks()
                self.assertEqual(a in tree.tree_state.expanded, opened)
            self.assertEqual(tree.tree_state.selected, a)
            for key in ('Arrow Right', 'Arrow Left', 'Enter', 'Space'):
                tree.tree_state.selected = a
                await tree._key(SimpleNamespace(key=key))
                await self.flush_callbacks()
                self.assertEqual(a in tree.tree_state.expanded, opened, key)
        tree.expandAll()
        await self.flush_callbacks()
        self.assertEqual(len(tree.tree_state.expanded), 2)
        tree.expandable(True)
        await self.flush_callbacks()
        await tree._key(SimpleNamespace(key='End'))
        self.assertEqual(tree.tree_state.selected, child)

    async def test_adapter_moves_delete_and_double_click(self):
        calls = []
        child = SimpleNamespace(text='child', children=[])
        a = SimpleNamespace(text='a', children=[child])
        b = SimpleNamespace(text='b', children=[])
        class Adapter(BaseTreeAdapter):
            roots = [a, b]
            def rowCount(self, parent): return len(self.roots if parent is None else parent.children)
            def child(self, parent, index): return (self.roots if parent is None else parent.children)[index]
            def data(self, node): return node.text
            def dblclicked(self, node): calls.append(node)
        adapter = Adapter()
        class Example(Application):
            def content(self):
                with Window():
                    Tree(adapter).expandAll()
        await self.mount(Example())
        tree = self.tree()
        tree.ui.focus = AsyncMock()
        key = self.key('child')
        hit = tree.rows[key].content.controls[1]
        await self.session.dispatch_event(hit._i, 'double_tap', None)
        await self.flush_callbacks()
        self.assertEqual(calls, [child])
        a.children.clear(); b.children.append(child)
        child.text = 'renamed'
        self.sync()
        tree = self.tree()
        self.assertEqual(self.key('renamed'), key)
        self.assertEqual(tree.tree_state.selected, key)
        self.assertEqual(tree.tree_state.entries[key].parent, self.key('b'))
        b.children.clear()
        self.sync()
        self.assertIsNone(self.tree().tree_state.selected)
        self.assertNotIn(key, self.tree().rows)
        self.assertFalse(self.tree().tree_event(key, 'clicked'))
