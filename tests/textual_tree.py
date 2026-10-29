"""env/bin/python -m unittest discover -s tests -p textual_tree.py -v"""
import unittest
import textual_views
from PUI.textual import Application, Window, Tree, TreeNode, BaseTreeAdapter


class TextualTreeTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = textual_views.TextualViewsTests.asyncSetUp
    asyncTearDown = textual_views.TextualViewsTests.asyncTearDown

    def tree(self):
        return self.root.children[0].children[0]

    def key(self, label):
        return next(k for k,e in self.tree().tree_state.entries.items() if e.text == label)

    async def test_keyboard_callbacks_redraw_and_commands(self):
        calls = []
        class Example(Application):
            order = ['a', 'b']
            version = 0
            def content(self):
                with Window():
                    with Tree():
                        for name in self.order:
                            with TreeNode(name).id(name).expand(calls.append, 'expand'):
                                TreeNode(name+' child').click(lambda e,v=self.version: calls.append(v))
        self.root = Example()
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            tree = self.tree()
            tree.ui.focus()
            a = self.key('a')
            tree.ui.move_cursor(tree._items[a])
            await pilot.press('space')
            await pilot.pause()
            self.assertIn(a, tree.tree_state.expanded)
            self.assertEqual(calls, ['expand'])
            await pilot.press('down', 'enter')
            await pilot.pause()
            child = self.key('a child')
            self.assertEqual(tree.tree_state.selected, child)
            self.assertEqual(calls[-1], 0)
            self.root.order.reverse(); self.root.version = 1
            self.root.redraw()
            await pilot.pause()
            tree = self.tree()
            self.assertEqual(tree.tree_state.selected, child)
            self.assertEqual(tree.ui.cursor_node.data, child)
            self.assertIn(a, tree.tree_state.expanded)
            await pilot.press('enter')
            await pilot.pause()
            self.assertEqual(calls[-1], 1)
            tree.collapseAll()
            await pilot.pause()
            self.assertFalse(tree.tree_state.expanded)
            tree.expandable(False)
            await pilot.pause()
            tree.ui.move_cursor(tree._items[a])
            await pilot.press('space')
            await pilot.pause()
            self.assertFalse(tree.tree_state.expanded)
            tree.expandAll()
            await pilot.pause()
            self.assertEqual(len(tree.tree_state.expanded), 2)

    async def test_native_expansion_batch_is_not_undone_during_event_dispatch(self):
        from unittest.mock import patch
        from contextlib import ExitStack
        calls = []
        class Example(Application):
            def content(self):
                with Window():
                    with Tree():
                        for name in ('a', 'b', 'c'):
                            with TreeNode(name).expand(calls.append, name):
                                TreeNode(name + ' child')
        self.root = Example()
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            tree = self.tree()
            items = [tree._items[self.key(name)] for name in ('a', 'b', 'c')]
            # Textual posts one message per node after changing native state.
            # No handler may undo the still-queued changes to other nodes.
            with ExitStack() as stack:
                reversals = [stack.enter_context(patch.object(item, 'collapse', wraps=item.collapse)) for item in items]
                for item in items:
                    item.expand()
                await pilot.pause()
                self.assertTrue(all(item.is_expanded for item in items))
                self.assertTrue(all(mock.call_count == 0 for mock in reversals))
            self.assertEqual(calls, ['a', 'b', 'c'])
            with ExitStack() as stack:
                reversals = [stack.enter_context(patch.object(item, 'expand', wraps=item.expand)) for item in items]
                for item in items:
                    item.collapse()
                await pilot.pause()
                self.assertTrue(all(item.is_collapsed for item in items))
                self.assertTrue(all(mock.call_count == 0 for mock in reversals))
            self.assertFalse(tree.tree_state.expanded)

    async def test_pointer_click_and_double_click(self):
        calls = []
        class Example(Application):
            def content(self):
                with Window():
                    with Tree().expandAll():
                        TreeNode('leaf').click(lambda e: calls.append('click')).dblclick(lambda e: calls.append('double'))
        self.root = Example()
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            tree = self.tree()
            await pilot.click(tree.ui, offset=(4, 0))
            await pilot.pause()
            self.assertIn('click', calls)
            await pilot.click(tree.ui, offset=(4, 0), times=2)
            await pilot.pause()
            self.assertIn('double', calls)

    async def test_adapter_structure_literal_labels_and_stale_events(self):
        from types import SimpleNamespace as Node
        calls = []
        child = Node(text='[red]literal', children=[])
        a, b = Node(text='a', children=[child]), Node(text='b', children=[])
        class Adapter(BaseTreeAdapter):
            roots = [a,b]
            def rowCount(self, parent): return len(self.roots if parent is None else parent.children)
            def child(self, parent, index): return (self.roots if parent is None else parent.children)[index]
            def data(self, node): return node.text
            def clicked(self, node): calls.append(node)
        adapter = Adapter()
        class Example(Application):
            def content(self):
                with Window(): Tree(adapter).expandAll()
        self.root = Example()
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            tree = self.tree(); key = self.key('[red]literal'); item = tree._items[key]
            self.assertEqual(item.label.plain, '[red]literal')
            tree.ui.select_node(item)
            await pilot.pause()
            self.assertEqual(calls, [child])
            a.children.clear(); b.children.append(child)
            child.text = 'renamed'
            self.root.redraw()
            await pilot.pause()
            tree = self.tree()
            self.assertEqual(self.key('renamed'), key)
            self.assertEqual(tree.tree_state.selected, key)
            self.assertEqual(tree.ui.cursor_node.data, key)
            self.assertEqual(tree._items[key].parent.data, self.key('b'))
            tree.ui.post_message(tree.ui.NodeSelected(item))
            await pilot.pause()
            self.assertEqual(calls, [child])
            b.children.clear(); self.root.redraw()
            await pilot.pause()
            self.assertNotIn(key, self.tree()._items)
