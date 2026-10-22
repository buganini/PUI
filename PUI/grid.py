"""Shared Grid auto-placement; computed cells never participate in vnode keys."""
from __future__ import annotations
from . import _typing as _t


class GridMixin:
    pui_grid_layout = True
    _grid_columns = None
    _grid_dense = None
    _grid_expand_children = True
    # Terminal overrides take precedence over shared defaults in either call order.
    # Width breakpoints preserve dense and expansion unless explicitly overridden.
    _grid_tcolumns_set = False
    _grid_tdense_set = False
    _grid_texpand_set = False

    def update(self, prev):
        self._grid_previous_auto = prev is not None and prev._grid_columns is not None
        super().update(prev)

    @staticmethod
    def _column_count(n):
        if type(n) is not int or n <= 0:
            raise ValueError('Grid columns must be a positive integer')
        return n

    def _set_columns(self, n, dense, expandChildren, terminal):
        self._column_count(n)
        if dense is not None and type(dense) is not bool:
            raise ValueError('Grid dense must be None, True or False')
        self._validate_expand(expandChildren)
        if terminal:
            if not self._terminal_units:
                return
            self._grid_tcolumns_set = self._grid_tdense_set = self._grid_texpand_set = True
        if not self._terminal_units or terminal or not self._grid_tcolumns_set:
            self._grid_columns = n
        if not self._terminal_units or terminal or not self._grid_tdense_set:
            self._grid_dense = dense
        if not self._terminal_units or terminal or not self._grid_texpand_set:
            self._grid_expand_children = expandChildren

    def columns(self: _t.NodeT, n: int, *, dense: bool | None = None, expandChildren: bool = True) -> _t.NodeT:
        """Set automatic columns and backfill; Textual inherits unless overridden."""
        self._set_columns(n, dense, expandChildren, False)
        return self

    def wideColumns(self: _t.NodeT, minWidth: _t.Number, n: int, *, expandChildren: bool | None = None) -> _t.NodeT:
        self._column_count(n)
        if expandChildren is not None:
            self._validate_expand(expandChildren)
        if self._wide_matches(minWidth, False, 'wideColumns'):
            self._grid_columns = n
            if expandChildren is not None:
                self._grid_expand_children = expandChildren
        return self

    def tColumns(self: _t.NodeT, n: int, *, dense: bool | None = None, expandChildren: bool = True) -> _t.NodeT:
        """Override Textual's column count and backfill (including dense=None)."""
        self._set_columns(n, dense, expandChildren, True)
        return self

    def tWideColumns(self: _t.NodeT, minWidth: int, n: int, *, expandChildren: bool | None = None) -> _t.NodeT:
        self._column_count(n)
        if expandChildren is not None:
            self._validate_expand(expandChildren)
        if self._wide_matches(minWidth, True, 'tWideColumns'):
            self._grid_columns = n
            self._grid_tcolumns_set = True
            if expandChildren is not None:
                self._grid_expand_children = expandChildren
                self._grid_texpand_set = True
        return self

    @staticmethod
    def _validate_expand(value):
        if type(value) is not bool:
            raise ValueError('Grid expandChildren must be a bool')

    def _expand_cells(self, cells, occupied):
        bottom = max((row + rows for _, (row, column, rows, cols) in cells), default=0)
        expanded = []
        for child, (row, column, rows, cols) in cells:
            while column + cols < self._grid_columns:
                edge = [(r, column + cols) for r in range(row, row + rows)]
                if any(position in occupied for position in edge):
                    break
                occupied.update(edge)
                cols += 1
            while row + rows < bottom:
                edge = [(row + rows, c) for c in range(column, column + cols)]
                if any(position in occupied for position in edge):
                    break
                occupied.update(edge)
                rows += 1
            child._grid_cell = cell = (row, column, rows, cols)
            expanded.append((child, cell))
        return expanded

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
        return self._expand_cells(cells, occupied) if self._grid_expand_children else cells
