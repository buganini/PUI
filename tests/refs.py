"""Named reference lifetime through actual VDOM reconciliation."""
import gc
import unittest
import weakref

import PUI
from PUI import PUINode, PUIView
from PUI.dom import recur_delete
from PUI.refs import NodeBinder, refs as registry


class Native(PUINode):
    def update(self, prev):
        self.ui = prev.ui if prev else object()
        super().update(prev)


class TestWindowBinder(NodeBinder):
    def maximize(self, enabled):
        self._node(enabled).last_command = 'maximize', enabled

    def minimize(self, enabled):
        self._node(enabled).last_command = 'minimize', enabled

    def fullscreen(self, enabled):
        self._node(enabled).last_command = 'fullscreen', enabled


class Window(Native):
    def __pui_binder__(self):
        return TestWindowBinder(self)


class Host(PUIView):
    show = True
    name_ref = 'test-ref'
    node_id = 'one'
    node_type = Native
    def content(self):
        if self.show:
            node = self.node_type().id(self.node_id)
            if self.name_ref is not None:
                node.ref(self.name_ref)


class RefTests(unittest.TestCase):
    def setUp(self):
        self.root = Host()

    def tearDown(self):
        recur_delete(self.root, self.root, True)
        self.assertNotIn('test-ref', registry)
        self.assertNotIn('renamed-ref', registry)

    def test_shared_backend_registry(self):
        import PUI.web as web
        import PUI.pyodide as pyodide
        from types import ModuleType
        self.assertIsInstance(PUI.refs, ModuleType)
        self.assertIs(PUI.refs.NodeBinder, NodeBinder)
        self.assertIs(PUI.ref, web.ref)
        self.assertIs(PUI.ref, pyodide.ref)

    def test_ref_get_returns_current_value_and_raises_when_missing(self):
        with self.assertRaises(KeyError):
            PUI.ref('test-ref')
        self.root.sync()
        first = PUI.ref('test-ref')
        self.assertIs(first.node, self.root.children[0])
        self.root.sync()
        self.assertIs(PUI.ref('test-ref').node, self.root.children[0])
        self.assertIsNot(PUI.ref('test-ref'), first)
        self.root.show = False
        self.root.sync()
        with self.assertRaises(KeyError):
            PUI.ref('test-ref')

    def test_key_format_and_debug_tag(self):
        node = Native()
        node._internal_tag = 'internal'
        node.grid(1, 2).id('item').ref('named').tag('debug only')
        self.assertEqual(node.key, 'Native:grid:1,2,None,None#tag=internal#id=item#ref=named')

    def test_publish_update_destroy(self):
        self.root.sync()
        old = registry['test-ref']
        old_node = old.node
        native = old.node.ui
        self.root.sync()
        new = registry['test-ref']
        self.assertIsNot(new, old)
        self.assertIs(new.node.ui, native)
        old_node.destroy(False)  # Must not erase the replacement's registration.
        self.assertIs(registry['test-ref'], new)
        self.root.show = False
        self.root.sync()
        self.assertNotIn('test-ref', registry)

    def test_rename_and_remove_rebuild(self):
        self.root.sync()
        old = self.root.children[0]
        self.root.name_ref = 'renamed-ref'
        self.root.sync()
        self.assertTrue(old.destroyed)
        self.assertNotIn('test-ref', registry)
        new = registry['renamed-ref'].node
        self.root.name_ref = None
        self.root.sync()
        self.assertTrue(new.destroyed)
        self.assertNotIn('renamed-ref', registry)

    def test_id_change_with_same_ref(self):
        self.root.sync()
        old = self.root.children[0]
        self.root.node_id = 'two'
        self.root.sync()
        self.assertTrue(old.destroyed)
        self.assertIs(registry['test-ref'].node, self.root.children[0])

    def test_window_ref_refreshes_binder_and_expires_on_destroy(self):
        self.root.node_type = Window
        self.root.sync()
        binder = registry['test-ref']
        self.root.sync()
        updated = registry['test-ref']
        self.assertIsNot(updated, binder)
        binder = updated
        binder.maximize(True)
        self.assertEqual(self.root.children[0].last_command, ('maximize', True))
        binder.fullscreen(False)
        binder.minimize(True)
        self.assertEqual(self.root.children[0].last_command, ('minimize', True))
        self.root.show = False
        self.root.sync()
        with self.assertRaises(RuntimeError):
            binder.maximize(False)

    def test_replacement_does_not_retarget_old_binder(self):
        self.root.node_type = Window
        self.root.sync()
        binder = registry['test-ref']
        self.root.node_id = 'replacement'
        self.root.sync()
        with self.assertRaises(RuntimeError):
            binder.minimize(True)
        registry['test-ref'].minimize(False)

    def test_no_registry_leak_after_dynamic_names(self):
        self.root.sync()
        old = weakref.ref(self.root.children[0])
        self.root.name_ref = 'renamed-ref'
        self.root.sync()
        gc.collect()
        self.assertIsNone(old())

    def test_duplicate_ref_overwrites_without_old_destroy_erasing_new(self):
        class Duplicate(PUIView):
            def content(self):
                Native().id('a').ref('test-ref')
                Native().id('b').ref('test-ref')
        root = Duplicate()
        try:
            root.sync()
            first, second = root.children
            self.assertIs(registry['test-ref'].node, second)
            first.destroy(False)
            self.assertIs(registry['test-ref'].node, second)
        finally:
            recur_delete(root, root, True)

    def test_replacement_keeps_old_ref_until_new_node_is_published(self):
        observations = []
        class Observe(Native):
            def update(self, prev):
                observations.append(registry.get('test-ref'))
                super().update(prev)
        self.root.node_type = Observe
        self.root.sync()
        old = registry['test-ref']
        old_node = old.node
        self.root.node_id = 'replacement'
        self.root.sync()
        self.assertEqual(observations, [None, old])
        self.assertTrue(old_node.destroyed)
        self.assertIs(registry['test-ref'].node, self.root.children[0])

    def test_scheduled_command_uses_current_node_and_skips_destroyed(self):
        pending, applied = [], []
        self.root.node_type = Window
        self.root.sync()
        binder = registry['test-ref']
        binder._post = pending.append
        binder._schedule(True, lambda node, enabled: applied.append(node))
        self.root.sync()
        self.assertIsNot(registry['test-ref'], binder)
        pending.pop(0)()
        self.assertEqual(applied, [self.root.children[0]])
        binder._schedule(False, lambda node, enabled: applied.append(node))
        self.root.show = False
        self.root.sync()
        pending.pop(0)()
        self.assertEqual(len(applied), 1)
        with self.assertRaises(RuntimeError):
            binder._schedule(True, lambda *_: None)

    def test_retained_view_reference(self):
        class Child(PUIView):
            def content(self):
                Native()
        self.root.node_type = Child
        self.root.sync()
        child = registry['test-ref']
        self.root.sync()
        self.assertIs(registry['test-ref'].node, child.node)


if __name__ == '__main__':
    unittest.main()
