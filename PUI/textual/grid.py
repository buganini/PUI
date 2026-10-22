"""Textual layout adapter for the shared explicit and automatic Grid cells."""
from fractions import Fraction
from textual.geometry import Region, NULL_OFFSET
from textual.layout import Layout, WidgetPlacement
from textual.widget import Widget
from ..grid import GridMixin
from .layout import VBox
from .base import TBase


class _GridLayout(Layout):
    name = 'pui-grid'

    def __init__(self):
        self.cells = []
        self.columns = 1

    def arrange(self, parent, children, size, greedy=True):
        cells = [(widget, cell) for widget, cell in self.cells if widget in children]
        columns = max(self.columns, max((c + cs for _, (_, c, _, cs) in cells), default=1))
        edges = [i * size.width // columns for i in range(columns + 1)]
        rows = [1] * max((r + rs for _, (r, _, rs, _) in cells), default=0)
        viewport = parent.app.viewport_size
        # Satisfy compact rows first, then distribute a spanning item's remaining
        # natural height among its rows. Placement is independent of vnode order.
        for widget, (row, column, rowspan, columnspan) in sorted(cells, key=lambda item: item[1][2]):
            styles = widget.styles
            width = max(1, edges[column + columnspan] - edges[column] - styles.margin.width)
            scalar = styles.height
            if scalar is not None and not scalar.is_auto and not scalar.is_fraction:
                height = int(scalar.resolve(size, viewport, Fraction(1)))
            else:
                height = widget.get_content_height(size, viewport, max(1, width - styles.gutter.width)) + styles.gutter.height
            deficit = max(0, height + styles.margin.height - sum(rows[row:row + rowspan]))
            for i in range(rowspan):
                rows[row + i] += deficit // rowspan + (i < deficit % rowspan)
        tops = [0]
        for height in rows:
            tops.append(tops[-1] + height)
        placements = []
        for order, (widget, (row, column, rowspan, columnspan)) in enumerate(cells):
            margin = widget.styles.margin
            region = Region(edges[column] + margin.left, tops[row] + margin.top,
                            max(0, edges[column + columnspan] - edges[column] - margin.width),
                            max(0, tops[row + rowspan] - tops[row] - margin.height))
            placements.append(WidgetPlacement(region, NULL_OFFSET, margin, widget, order))
        return placements


class _GridWidget(Widget):
    def __init__(self):
        self.grid_layout = _GridLayout()
        super().__init__()

    @property
    def layout(self):
        return self.grid_layout


class Grid(GridMixin, VBox):
    container_y = False
    expand_x_prio = 3
    expand_y_prio = 1

    def update(self, prev):
        self.ui = prev.ui if prev is not None else _GridWidget()
        self._grid_previous_auto = prev is not None and prev._grid_columns is not None
        TBase.update(self, prev)
        self.mounted = prev.mounted if prev is not None else []
        self.grid_layout = self.ui.grid_layout

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)
        super().addChild(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        super().removeChild(idx, child)

    def moveChild(self, source, target, child):
        self.mounted.insert(target, self.mounted.pop(source))
        super().moveChild(source, target, child)

    def postSync(self):
        self.grid_layout.cells = [(child.outer, cell) for child, cell in self.grid_cells(self.mounted) if child._visible]
        self.grid_layout.columns = self._grid_columns or 1
        self.ui.refresh(layout=True)
        super().postSync()
