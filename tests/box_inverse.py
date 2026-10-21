"""DOM fallback keeps native identity across dynamic and inherited reversal."""
import contextlib
import io
import unittest

from PUI import PUINode, PUIView
from PUI.adaptive import BoxMixin
from PUI.dom import recur_delete


class Cell(PUINode):
    pui_terminal = True

    def update(self, prev):
        self.ui = prev.ui if prev is not None else {'value': self.args[0], 'draft': ''}
        super().update(prev)


class Host(BoxMixin, PUINode):
    def update(self, prev):
        self.ui = prev.ui if prev is not None else []
        super().update(prev)

    def addChild(self, idx, child):
        if not child.pui_outoforder:
            self.ui.insert(idx, child.ui)

    def removeChild(self, idx, child):
        if not child.pui_outoforder:
            assert self.ui[idx] is child.ui, (idx, child.args, self.ui)
            self.ui.pop(idx)


class InverseDOM(unittest.TestCase):
    def sync(self, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            root.sync()
        self.assertNotIn('<ERROR', output.getvalue())

    def test_same_keys_preserve_declaration_occurrences_and_static_default(self):
        for static_reverse in (False, True):
            class Box(Host):
                pui_reversed_order = static_reverse
            class Demo(PUIView):
                inverse = False
                def content(self):
                    with Box(inverse=self.inverse):
                        for name in ('A', 'B', 'C'):
                            Cell(name)  # Deliberately identical keys.
            root = Demo()
            try:
                self.sync(root)
                native = {cell.args[0]: cell.ui for cell in root.children[0].children}
                native['B']['draft'] = 'uncommitted'
                for inverse in (True, True, False, False, True, False):
                    root.inverse = inverse
                    self.sync(root)
                    box = root.children[0]
                    order = ['C', 'B', 'A'] if inverse ^ static_reverse else ['A', 'B', 'C']
                    self.assertEqual([ui['value'] for ui in box.ui], order)
                    for cell in box.children:
                        self.assertIs(cell.ui, native[cell.args[0]])
                    self.assertEqual(native['B']['draft'], 'uncommitted')
                    self.assertIs(type(box).pui_reversed_order, static_reverse)
            finally:
                recur_delete(root, root, True)

    def test_nested_virtual_views_and_independent_updates(self):
        class Inner(PUIView):
            names = ['X', 'Y']
            def content(self):
                for name in self.names:
                    Cell(name).id(name)
        class Fragment(PUIView):
            def content(self):
                Cell('L').id('left')
                Inner()
                Cell('R').id('right')
        class Demo(PUIView):
            inverse = False
            def content(self):
                with Host(inverse=self.inverse):
                    Cell('A').id('a')
                    Fragment()
                    Cell('B').id('b')
        root = Demo()
        try:
            self.sync(root)
            for inverse in (True, False, True):
                root.inverse = inverse
                self.sync(root)
                box = root.children[0]
                order = ['A', 'L', 'X', 'Y', 'R', 'B']
                self.assertEqual([ui['value'] for ui in box.ui], order[::-1] if inverse else order)
            fragment = next(child for child in box.children if isinstance(child, Fragment))
            inner = next(child for child in fragment.children if isinstance(child, Inner))
            for names in (['Y', 'Z', 'X'], [], ['X']):
                inner.names = names
                self.sync(inner)
                self.assertEqual([ui['value'] for ui in box.ui], ['B', 'R', *names[::-1], 'L', 'A'])
        finally:
            recur_delete(root, root, True)

    def test_view_inside_nested_virtual_scopes_reorders_and_changes_roots(self):
        class Scope(PUINode):
            pui_virtual = True
        class Fragment(PUIView):
            names = ('B', 'C', 'D')
            def content(self):
                with Scope():
                    with Scope():
                        for name in self.names:
                            Cell(name).id(name)
        class Demo(PUIView):
            inverse = False
            def content(self):
                with Host(inverse=self.inverse):
                    Cell('A').id('a')
                    with Scope():
                        Fragment()
                    Cell('Z').id('z')
        root = Demo()
        try:
            self.sync(root)
            scope = root.children[0].children[1]
            fragment = scope.children[0]
            for inverse in (True, False, True):
                root.inverse = inverse
                self.sync(root)
                self.assertIs(next(c for c in root.children[0].children
                                   if isinstance(c, Scope)).children[0], fragment)
                for names in (('D', 'B', 'C'), ('B',), (), ('B', 'C', 'D')):
                    fragment.names = names
                    self.sync(fragment)
                    expected = ['A', *names, 'Z']
                    self.assertEqual([ui['value'] for ui in root.children[0].ui],
                                     expected[::-1] if inverse else expected)
        finally:
            recur_delete(root, root, True)

    def test_hidden_reversal_applies_when_children_thaw(self):
        class Demo(PUIView):
            inverse = False
            visible = True
            def content(self):
                with Host(inverse=self.inverse).visible(self.visible):
                    Cell('A')
                    Cell('B')
        root = Demo()
        try:
            self.sync(root)
            originals = list(root.children[0].ui)
            root.visible, root.inverse = False, True
            self.sync(root)
            self.assertEqual(root.children[0].ui, originals)
            root.visible = True
            self.sync(root)
            self.assertEqual(root.children[0].ui, originals[::-1])
        finally:
            recur_delete(root, root, True)

    def test_reversal_refresh_stops_at_physical_container_and_defers_frozen_view(self):
        calls = {'fragment': 0, 'inner': 0}
        class Inner(PUIView):
            def content(self):
                calls['inner'] += 1
                Cell('X')
                Cell('Y')
        class Fragment(PUIView):
            def content(self):
                calls['fragment'] += 1
                Cell('A')
                with Host():
                    Inner()
                Cell('B')
        class Demo(PUIView):
            inverse = False
            frozen = False
            def content(self):
                with Host(inverse=self.inverse):
                    fragment = Fragment()
                    fragment.pui_frozen = self.frozen
        root = Demo()
        try:
            self.sync(root)
            fragment = root.children[0].children[0]
            nested = fragment.children[1].ui
            self.assertEqual(calls, {'fragment': 1, 'inner': 1})
            root.inverse = True
            self.sync(root)
            self.assertEqual(calls, {'fragment': 2, 'inner': 1})
            self.assertEqual([item['value'] for item in nested], ['X', 'Y'])
            self.assertIs(fragment._prev_reversed_order, True)
            root.frozen, root.inverse = True, False
            self.sync(root)
            self.assertIs(fragment._prev_reversed_order, True)
            self.assertEqual(calls['fragment'], 2)
            root.frozen = False
            self.sync(root)
            self.assertIs(fragment._prev_reversed_order, False)
            self.assertEqual(calls['fragment'], 3)
        finally:
            recur_delete(root, root, True)

    def test_failed_content_keeps_old_order_and_discards_partial_view(self):
        class Unmounted(PUIView):
            pass
        class Fragment(PUIView):
            fail = False
            def content(self):
                Cell('A')
                if self.fail:
                    Unmounted()
                    raise RuntimeError('deliberate content failure')
                Cell('B')
        class Demo(PUIView):
            inverse = False
            def content(self):
                with Host(inverse=self.inverse):
                    Fragment()
        root = Demo()
        try:
            self.sync(root)
            fragment = root.children[0].children[0]
            original = list(root.children[0].ui)
            fragment.fail = True
            root.inverse = True
            for _ in range(2):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    root.sync()
                self.assertIn('deliberate content failure', output.getvalue())
                self.assertEqual(root.children[0].ui, original)
                self.assertIs(fragment._prev_reversed_order, False)
                self.assertFalse(fragment.updating)
                self.assertFalse(any(isinstance(view, Unmounted) for view in PUIView.__ALLVIEWS__))
            fragment.fail = False
            self.sync(root)
            self.assertEqual(root.children[0].ui, original[::-1])
            self.assertIs(fragment._prev_reversed_order, True)
        finally:
            recur_delete(root, root, True)

    def test_previous_order_is_published_only_after_sync_succeeds(self):
        class Box(Host):
            fail = False
            def postSync(self):
                if self.fail:
                    raise RuntimeError('deliberate postSync failure')
        class Demo(PUIView):
            inverse = False
            def content(self):
                with Box(inverse=self.inverse) as self.box:
                    self.box.fail = self.inverse
                    Cell('A')
                    Cell('B')
        root = Demo()
        try:
            self.sync(root)
            root.inverse = True
            with self.assertRaisesRegex(RuntimeError, 'postSync failure'):
                root.sync()
            self.assertIs(root.box._prev_reversed_order, False)
        finally:
            recur_delete(root, root, True)
