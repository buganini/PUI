"""Cached flattened offsets agree with traversal across structural updates."""
import random
import unittest
from unittest.mock import patch

from PUI import PUINode, PUIView
from PUI.dom import recur_delete


class Native(PUINode):
    pass


class Inner(PUIView):
    def content(self):
        index, widths = self.args
        for j in range(widths[index]):
            Native().id(str(j))


class Fragment(PUIView):
    def content(self):
        Native().id('before')
        Inner(*self.args)
        Native().id('after')


class Host(PUIView):
    def setup(self):
        self.order = list(range(20))
        self.widths = {i: 3 for i in self.order}

    def content(self):
        with Native():
            for i in self.order:
                Fragment(i, self.widths).id(str(i))


class OffsetCacheTests(unittest.TestCase):
    def test_hit_and_parent_identity(self):
        parent, other, target = Native(), Native(), Native()
        parent.children = [target]
        self.assertEqual(parent.findDomOffsetForNode(target), (True, 0))
        with patch.object(parent, '_findDomOffsetForNode', side_effect=AssertionError):
            self.assertEqual(parent.findDomOffsetForNode(target), (True, 0))
        self.assertEqual(other.findDomOffsetForNode(target), (False, 0))

    def test_reversed_and_grid_normalization(self):
        for grid, reverse in ((False, True), (True, False)):
            root = Host()
            try:
                root.sync()
                parent = root.children[0]
                parent.pui_grid_layout = grid
                parent.pui_reversed_order = reverse
                for index, child in enumerate(parent.children):
                    if grid:
                        child.grid_row = 20 - index
                        child.grid_column = 0
                    parent.findDomOffsetForNode(child)
                from PUI.dom import sync
                children = list(parent.children)
                sync(parent, parent, 0, parent.children, children)
                for child in children:
                    self.assertEqual(parent.findDomOffsetForNode(child),
                                     parent._findDomOffsetForNode(child))
            finally:
                recur_delete(root, root, True)

    def test_nested_mutations_and_retirement(self):
        root = Host()
        rng = random.Random(42)
        removed = []
        try:
            root.sync()
            for step in range(200):
                parent = root.children[0]
                targets = [f.children[1] for f in parent.children]
                for target in targets:
                    self.assertEqual(parent.findDomOffsetForNode(target),
                                     parent._findDomOffsetForNode(target))
                action = step % 4
                if action == 0:
                    target = rng.choice(targets)
                    root.widths[target.args[0]] = rng.randrange(6)
                    old_children = list(target.children)
                    for child in old_children:
                        target.findDomOffsetForNode(child)
                    target.sync()
                    for child in old_children:
                        self.assertEqual(target.findDomOffsetForNode(child),
                                         target._findDomOffsetForNode(child))
                elif action == 1:
                    rng.shuffle(root.order)
                    root.sync()
                elif action == 2:
                    index = 20 + step
                    root.widths[index] = rng.randrange(6)
                    root.order.insert(rng.randrange(len(root.order) + 1), index)
                    root.sync()
                else:
                    index = rng.choice(root.order)
                    removed.extend(t for t in targets if t.args[0] == index)
                    root.order.remove(index)
                    root.sync()
                parent = root.children[0]
                for target in targets + removed[-3:]:
                    self.assertEqual(parent.findDomOffsetForNode(target),
                                     parent._findDomOffsetForNode(target))
                # Retiring same-key native nodes must not retain successful hits.
                fragment = parent.children[-1]
                old = fragment.children[0]
                parent.findDomOffsetForNode(old)
                fragment.sync()
                self.assertEqual(parent.findDomOffsetForNode(old),
                                 parent._findDomOffsetForNode(old))
        finally:
            recur_delete(root, root, True)


if __name__ == '__main__':
    unittest.main()
