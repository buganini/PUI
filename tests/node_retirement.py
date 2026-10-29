"""Retired callback handles must not keep intermediate generations alive."""
import gc
import unittest
import weakref

from PUI.node import PUINode


class NodeRetirementTests(unittest.TestCase):
    def test_idle_callback_handle_does_not_retain_generations(self):
        first = current = PUINode()
        refs = []
        for _ in range(200):
            following = PUINode()
            following.update(current)
            current.releaseRetiredRefs()
            refs.append(weakref.ref(current))
            current = following
        # No get_node() calls: an idle native callback still holds first.
        gc.collect()
        self.assertEqual(sum(ref() is not None for ref in refs), 1)
        self.assertIs(first.retired_by, current)
        self.assertIs(first.get_node(), current)

    def test_multiple_old_handles_follow_current_and_release_it(self):
        handles = [PUINode()]
        refs = []
        current = handles[0]
        for i in range(100):
            following = PUINode()
            following.update(current)
            current.releaseRetiredRefs()
            refs.append(weakref.ref(current))
            current = following
            if i in (20, 50):
                handles.append(current)
        gc.collect()
        self.assertEqual(sum(ref() is not None for ref in refs), len(handles))
        for handle in handles:
            self.assertIs(handle.get_node(), current)
        current.destroy(True)
        self.assertTrue(all(handle.get_node().destroyed for handle in handles))
        last = weakref.ref(current)
        del current, following, handle
        handles.clear()
        gc.collect()
        self.assertIsNone(last())
        self.assertTrue(all(ref() is None for ref in refs))

