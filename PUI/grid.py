"""Shared Grid auto-placement; computed cells never participate in vnode keys."""
from __future__ import annotations
from . import _typing as _t


class GridMixin:
    pui_grid_layout = True
    _grid_columns = None
    _grid_dense = None

    def update(self, prev):
        self._grid_previous_auto = prev is not None and prev._grid_columns is not None
        super().update(prev)

    @staticmethod
    def _column_count(n):
        if type(n) is not int or n <= 0:
            raise ValueError('Grid columns must be a positive integer')
        return n

    def _set_columns(self, n, dense, terminal):
        self._column_count(n)
        if dense is not None and type(dense) is not bool:
            raise ValueError('Grid dense must be None, True or False')
        if self._terminal_units == terminal:
            self._grid_columns = n
            self._grid_dense = dense

    def columns(self: _t.NodeT, n: int, *, dense: bool | None = None) -> _t.NodeT:
        self._set_columns(n, dense, False)
        return self

    def wideColumns(self: _t.NodeT, minWidth: _t.Number, n: int) -> _t.NodeT:
        self._column_count(n)
        if self._wide_matches(minWidth, False):
            self._grid_columns = n
        return self

    def tColumns(self: _t.NodeT, n: int, *, dense: bool | None = None) -> _t.NodeT:
        self._set_columns(n, dense, True)
        return self

    def tWideColumns(self: _t.NodeT, minWidth: int, n: int) -> _t.NodeT:
        self._column_count(n)
        if self._wide_matches(minWidth, True):
            self._grid_columns = n
        return self

    def grid_cells(self, children):
        """Return mounted children and effective cells in declaration order."""
        children = [child.get_node() for child in children]
        for child in children:
            child._grid_cell = None
        if self._grid_columns is None:
            return [(child, (child.grid_row, child.grid_column,
                             child.grid_rowspan or 1, child.grid_columnspan or 1))
                    for child in children
                    if child.grid_row is not None and child.grid_column is not None]
        cells, occupied, cursor, previous_row = [], set(), 0, 0
        columns = self._grid_columns
        for child in children:
            if not child._visible:
                continue
            rowspan = 1 if child.grid_rowspan is None else child.grid_rowspan
            columnspan = 1 if child.grid_columnspan is None else child.grid_columnspan
            if type(rowspan) is not int or type(columnspan) is not int or min(rowspan, columnspan) < 1:
                raise ValueError('Grid spans must be positive integers')
            columnspan = min(columns, columnspan)
            position = (0 if self._grid_dense is True else
                        cursor if self._grid_dense is False else previous_row * columns)
            while True:
                row, column = divmod(position, columns)
                if column + columnspan <= columns and all(
                        (r, c) not in occupied
                        for r in range(row, row + rowspan)
                        for c in range(column, column + columnspan)):
                    break
                position += 1
            occupied.update((r, c) for r in range(row, row + rowspan)
                            for c in range(column, column + columnspan))
            cursor = position + columnspan
            previous_row = row
            child._grid_cell = cell = (row, column, rowspan, columnspan)
            cells.append((child, cell))
        return cells
