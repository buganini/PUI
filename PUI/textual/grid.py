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
        self.node = None

    @staticmethod
    def distribute(sizes, start, span, extra, weights):
        selected = weights[start:start + span]
        if not any(selected):
            selected = [1] * span
        total, before, accumulated = sum(selected), 0, 0
        for index, weight in enumerate(selected, start):
            accumulated += weight
            after = round(extra * accumulated / total)
            sizes[index] += after - before
            before = after

    @staticmethod
    def measure(widget, axis, size, viewport, width=0):
        styles = widget.styles
        dimension = 'width' if axis == 'x' else 'height'
        scalar = getattr(styles, dimension)
        if scalar is not None and not scalar.is_auto and not scalar.is_fraction:
            extent = int(scalar.resolve(size, viewport, Fraction(1)))
        elif axis == 'x':
            extent = widget.get_content_width(size, viewport) + styles.gutter.width
        else:
            extent = widget.get_content_height(size, viewport, max(1, width - styles.gutter.width)) + styles.gutter.height
        minimum = getattr(styles, 'min_' + dimension)
        if minimum is not None and not minimum.is_auto and not minimum.is_fraction:
            extent = max(extent, int(minimum.resolve(size, viewport, Fraction(1))))
        return extent + getattr(styles.margin, dimension)

    def arrange(self, parent, children, size, greedy=True):
        cells = [(node, cell) for node, cell in self.cells if node.outer in children and node._visible]
        x_weights, y_weights = self.node.grid_stretches(cells)
        columns, rows = [0] * len(x_weights), [0] * len(y_weights)
        viewport = parent.app.viewport_size
        # Measure single tracks before spans. Spanning deficits go to eligible
        # tracks, without widening an unrelated static label column.
        for node, (_, column, _, columnspan) in sorted(cells, key=lambda item: item[1][3]):
            width = self.measure(node.outer, 'x', size, viewport)
            deficit = max(0, width - sum(columns[column:column + columnspan]))
            self.distribute(columns, column, columnspan, deficit, x_weights)
        if any(x_weights):
            self.distribute(columns, 0, len(columns), max(0, size.width - sum(columns)), x_weights)
        edges = [0]
        for width in columns:
            edges.append(edges[-1] + width)
        for node, (row, column, rowspan, columnspan) in sorted(cells, key=lambda item: item[1][2]):
            width = edges[column + columnspan] - edges[column] - node.outer.styles.margin.width
            height = self.measure(node.outer, 'y', size, viewport, width)
            deficit = max(0, height - sum(rows[row:row + rowspan]))
            self.distribute(rows, row, rowspan, deficit, y_weights)
        if any(y_weights):
            self.distribute(rows, 0, len(rows), max(0, size.height - sum(rows)), y_weights)
        tops = [0]
        for height in rows:
            tops.append(tops[-1] + height)
        placements = []
        for order, (node, (row, column, rowspan, columnspan)) in enumerate(cells):
            widget = node.outer
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
    expand_x_prio = expand_y_prio = 1

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
        self.grid_layout.node = self
        self.grid_layout.cells = self.grid_cells(self.mounted)
        self.ui.refresh(layout=True)
        super().postSync()
