"""Shared boolean visibility and independent Textual cell bounds."""
import unittest

from PUI.node import PUINode


class TerminalNode(PUINode):
    _terminal_units = True


class TerminalVisibilityTests(unittest.TestCase):
    def node(self, terminal=True):
        parent = PUINode()
        node = TerminalNode() if terminal else PUINode()
        node.parent = parent
        return node, parent

    def test_boolean_override_and_inheritance_in_both_call_orders(self):
        for shared in (False, True):
            for override in (None, False, True):
                for terminal_first in (False, True):
                    with self.subTest(shared=shared, override=override, terminal_first=terminal_first):
                        node, parent = self.node()
                        if terminal_first:
                            node.tVisible(override)
                        node.visible(shared, minWidth=9999, maxHeight=1)
                        if not terminal_first:
                            node.tVisible(override)
                        expected = shared if override is None else override
                        self.assertEqual(node._visible, expected)
                        self.assertEqual(node.pui_frozen, not expected)
                        self.assertIsNone(parent._state)  # Pixel limits never observe terminal sizes.

    def test_terminal_defaults_and_reset(self):
        node, _ = self.node()
        self.assertTrue(node.tVisible()._visible)
        self.assertFalse(node.visible(False)._visible)
        self.assertTrue(node.tVisible(True)._visible)
        self.assertFalse(node.tVisible()._visible)
        self.assertFalse(node.tVisible(False).visible(True)._visible)
        self.assertTrue(node.tVisible(None)._visible)
        self.assertTrue(TerminalNode().visible()._visible)

    def test_cell_bounds_unknown_size_and_boolean_changes(self):
        node, parent = self.node()
        limits = dict(minWidth=60, maxWidth=80, minHeight=20, maxHeight=30)
        node.visible(False).tVisible(True, **limits)
        self.assertIsNotNone(parent._state)
        self.assertFalse(node._visible)
        self.assertTrue(node.pui_frozen)
        for width, height, expected in ((59,20,False), (60,19,False), (60,20,True),
                                        (79,29,True), (80,20,False), (60,30,False)):
            with self.subTest(width=width, height=height):
                parent._set_size(width, height)
                node.tVisible(True, **limits)
                self.assertEqual(node._visible, expected)
                self.assertEqual(node.pui_frozen, not expected)
        parent._set_size(70, 25)
        node.tVisible(**limits)
        self.assertFalse(node._visible)  # Inherit the shared False.
        node.visible(True)
        self.assertTrue(node._visible)
        parent._set_size(80, 25)
        node.visible(True)
        self.assertFalse(node._visible)  # visible() must preserve terminal limits.
        self.assertTrue(node.tVisible()._visible)  # A new tVisible() replaces its settings.

    def test_graphical_backend_ignores_terminal_settings(self):
        node, parent = self.node(terminal=False)
        self.assertIs(node.tVisible(False, minWidth=9999), node)
        self.assertTrue(node._visible)
        self.assertIsNone(parent._state)
        parent._ensure_size()
        parent._set_size(80, 25)
        node.visible(maxWidth=60).tVisible(True)
        self.assertFalse(node._visible)
        self.assertTrue(node.pui_frozen)
        node.tVisible(False).visible(minWidth=60)
        self.assertTrue(node._visible)
        self.assertFalse(node.pui_frozen)

    def test_visible_rejects_removed_terminal_bounds(self):
        for name in ('tMinWidth', 'tMaxWidth', 'tMinHeight', 'tMaxHeight'):
            with self.subTest(name=name), self.assertRaises(TypeError):
                PUINode().visible(**{name: 60})
