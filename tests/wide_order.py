"""Breakpoint diagnostics preserve declaration order and avoid redraw log spam."""
import unittest
from PUI.node import PUINode, _warn_wide_order
from PUI.grid import GridMixin


class GridNode(GridMixin, PUINode):
    pass


class WideOrderTests(unittest.TestCase):
    def setUp(self):
        _warn_wide_order.cache_clear()

    def test_all_methods_warn_even_without_matching_size(self):
        for method in ('wideStyle', 'tWideStyle', 'wideLayout', 'tWideLayout',
                       'wideVisible', 'tWideVisible', 'wideGrid', 'tWideGrid',
                       'wideColumns', 'tWideColumns'):
            with self.subTest(method=method):
                node = GridNode()
                args = (False,) if method.endswith('Visible') else (2,) if method.endswith('Columns') else ()
                getattr(node, method)(100, *args)
                with self.assertLogs('PUI', level='WARNING') as logs:
                    getattr(node, method)(50, *args)
                self.assertIn(method + ' breakpoint 50 follows 100', logs.output[0])

    def test_equal_ascending_and_independent_methods_are_quiet(self):
        node = PUINode()
        with self.assertNoLogs('PUI'):
            node.wideStyle(100).wideStyle(100).wideStyle(200)
            node.wideLayout(10).tWideStyle(5).wideVisible(1, True)

    def test_redraw_deduplication_and_override_behavior(self):
        parent = PUINode()
        parent._ensure_size()
        parent._set_size(1000, 100)
        def declare():
            node = PUINode()
            node.parent = parent
            return node.wideStyle(800, fontSize=20).wideStyle(600, fontSize=16)
        with self.assertLogs('PUI', level='WARNING'):
            node = declare()
        self.assertEqual(node.style_fontsize, 16)
        with self.assertNoLogs('PUI'):
            declare()
        self.assertEqual(_warn_wide_order.cache_info().maxsize, 128)
