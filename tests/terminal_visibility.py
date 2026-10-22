"""Shared visibility, backend-specific width rules and frozen state."""
import unittest
from PUI.node import PUINode


class TerminalNode(PUINode):
    _terminal_units = True


class TerminalVisibilityTests(unittest.TestCase):
    def test_boolean_override_and_inheritance_in_both_call_orders(self):
        for shared in (False, True):
            for override in (None, False, True):
                for terminal_first in (False, True):
                    node = TerminalNode()
                    if terminal_first:
                        node.tVisible(override)
                    node.visible(shared)
                    if not terminal_first:
                        node.tVisible(override)
                    expected = shared if override is None else override
                    self.assertEqual(node._visible, expected)
                    self.assertEqual(node.pui_frozen, not expected)

    def test_terminal_default_and_reset(self):
        node = TerminalNode().visible(False)
        self.assertTrue(node.tVisible(True)._visible)
        self.assertFalse(node.tVisible(None)._visible)

    def test_width_rules_boundary_order_and_unknown_size(self):
        for cls, method in ((PUINode, 'wideVisible'), (TerminalNode, 'tWideVisible')):
            parent = PUINode()
            for width, expected in ((None, False), (59, False), (60, True), (79, True), (80, False)):
                node = cls()
                node.parent = parent
                if width is not None:
                    parent._set_size(width, 100)
                node.visible(False)
                getattr(node, method)(60, True)
                getattr(node, method)(80, False)
                self.assertEqual(node._visible, expected)
                self.assertEqual(node.pui_frozen, not expected)
            # Unknown size leaves the declared baseline unchanged.
            node = cls()
            node.parent = PUINode()
            self.assertTrue(getattr(node, method)(60, False)._visible)

    def test_other_backend_rules_do_not_observe_parent(self):
        for cls, method in ((PUINode, 'tWideVisible'), (TerminalNode, 'wideVisible')):
            node = cls()
            node.parent = PUINode()
            getattr(node, method)(60, False)
            self.assertTrue(node._visible)
            self.assertIsNone(node.parent._state)
        self.assertTrue(PUINode().tVisible(False)._visible)

    def test_removed_bounds_are_rejected(self):
        for method in ('visible', 'tVisible'):
            for name in ('minWidth', 'maxWidth', 'minHeight', 'maxHeight'):
                with self.assertRaises(TypeError):
                    getattr(PUINode(), method)(**{name: 60})
