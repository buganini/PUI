"""Shared placement and stable vnode identity, without a GUI dependency."""
import unittest
from types import SimpleNamespace
from PUI.grid import GridMixin


class GridPlacement(unittest.TestCase):
    def item(self, rowspan=1, columnspan=1, visible=True):
        item = SimpleNamespace(grid_row=99, grid_column=99, grid_rowspan=rowspan,
                               grid_columnspan=columnspan, _visible=visible)
        item.get_node = lambda: item
        return item

    def grid(self, n, dense=True):
        grid = GridMixin()
        grid._grid_columns = n
        grid.dense(dense)
        return grid

    def test_dense_backfills_a_hole_without_changing_declared_coordinates(self):
        items = [self.item(columnspan=2), self.item(columnspan=2), self.item()]
        grid = self.grid(3)
        self.assertEqual([cell for _, cell in grid.grid_cells(items)],
                         [(0, 0, 1, 2), (1, 0, 1, 2), (0, 2, 1, 1)])
        self.assertTrue(all(item.grid_row == item.grid_column == 99 for item in items))
        grid.dense(False)
        self.assertEqual(grid.grid_cells(items)[-1][1], (1, 2, 1, 1))

    def test_none_does_not_backfill_above_previous_row_but_can_fill_to_its_left(self):
        grid = self.grid(3, None)
        items = [self.item(columnspan=2), self.item(columnspan=2), self.item()]
        self.assertEqual(grid.grid_cells(items)[-1][1], (1, 2, 1, 1))
        items = [self.item(), self.item(rowspan=2), self.item(columnspan=2),
                 self.item(columnspan=2), self.item()]
        grid = self.grid(4, None)
        self.assertEqual(grid.grid_cells(items)[-1][1], (1, 0, 1, 1))
        grid.dense(False)
        self.assertEqual(grid.grid_cells(items)[-1][1], (2, 0, 1, 1))
        self.assertIs(GridMixin()._grid_dense, None)
        for invalid in ('true', 1, []):
            with self.assertRaises(ValueError):
                grid.dense(invalid)

    def test_row_spans_hidden_items_and_narrow_span_clamping(self):
        items = [self.item(rowspan=2, columnspan=2), self.item(), self.item(visible=False), self.item()]
        grid = self.grid(3)
        self.assertEqual([cell for _, cell in grid.grid_cells(items)],
                         [(0, 0, 2, 2), (0, 2, 1, 1), (1, 2, 1, 1)])
        self.assertIsNone(items[2]._grid_cell)
        grid._grid_columns = 1
        self.assertEqual(grid.grid_cells(items)[0][1], (0, 0, 2, 1))
        grid._grid_columns = 3
        self.assertEqual(grid.grid_cells(items)[0][1], (0, 0, 2, 2))
        self.assertEqual(items[0].grid_columnspan, 2)

    def test_invalid_spans(self):
        for n in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.grid(3).grid_cells([self.item(rowspan=n)])
            with self.assertRaises(ValueError):
                self.grid(3).grid_cells([self.item(columnspan=n)])

    def test_invalid_counts(self):
        for n in (0, -1, True, 1.5, '3'):
            with self.assertRaises(ValueError):
                GridMixin._column_count(n)

    def test_rules_follow_declaration_order_and_terminal_units(self):
        class Grid(GridMixin):
            _terminal_units = False
            def _wide_matches(self, width, terminal):
                return terminal == self._terminal_units and 800 >= width
        grid = Grid().columns(1).wideColumns(700, 3).wideColumns(600, 2)
        self.assertEqual(grid._grid_columns, 2)
        grid.tColumns(7)
        self.assertEqual(grid._grid_columns, 2)
        grid._terminal_units = True
        grid.tColumns(1).tWideColumns(60, 3).columns(8)
        self.assertEqual(grid._grid_columns, 3)
