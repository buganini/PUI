from ..grid import GridMixin
from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *


def _sticky(child):
    return getattr(child, 'grid_sticky', 'nsew')

def _priority(child, axis):
    if child.layout_weight is not None:
        return 4 if child.layout_weight > 0 else 0
    return getattr(child, f'expand_{axis}_prio', 0)


def _linear_options(parent, child, axis):
    highest = parent._main_priority
    grows = highest > 0 and _priority(child, axis) == highest
    weight = (child.layout_weight if child.layout_weight is not None else 1) if grows else 0
    cross = 'y' if axis == 'x' else 'x'
    stretches = getattr(child, f'expand_{cross}_prio', 0) > 0
    sticky = ('ew' if axis == 'x' else 'ns') if grows else ''
    if stretches:
        sticky += 'ns' if axis == 'x' else 'ew'
    if axis == 'y' and not stretches:
        sticky += 'w'
    return weight, sticky


class HBox(_BoxMixin, TkBaseWidget):
    expand_x_prio = 2
    expand_y_prio = 1
    pui_terminal = False

    ttk_style = "TFrame"
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui_children = prev.ui_children
            self.ui_gridmap = prev.ui_gridmap
        else:
            self.ui = ttk.Frame(self.tkparent.inner)
            self.ui.grid_rowconfigure(0, weight=1)
            self.ui_children = []
            self.ui_gridmap = set()
        super().update(prev)

    def addChild(self, idx, child):
        self.ui_children.insert(idx, child)

    def removeChild(self, idx, child):
        self.ui_children.pop(idx)
        if isinstance(child, TkBaseWidget):
            child_outer = child.outer
            if child_outer:
                child_outer.grid_forget()

    def putChild(self, idx, child):
        if isinstance(child, TkBaseWidget):
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            if not child._visible:
                child.outer.grid_remove()
                self.ui.grid_columnconfigure(idx, weight=0, uniform="")
                self.ui_gridmap.discard(idx)
                return
            weight, sticky = _linear_options(self, child, 'x')
            child.outer.grid(row=0, column=idx, sticky=sticky, padx=(left, right), pady=(top, bottom))
            self.ui.grid_columnconfigure(idx, weight=weight, uniform="." if child.layout_weight and weight else "")
            if weight:
                self.ui_gridmap.add(idx)
            else:
                self.ui_gridmap.discard(idx)

    def postSync(self):
        n = len(self.ui_children)
        tbd = []
        for i in self.ui_gridmap:
            if i >= n:
                self.ui.grid_columnconfigure(i, weight=0, uniform="")
                tbd.append(i)
        for i in tbd:
            self.ui_gridmap.discard(i)

        self.ui_children[:] = [child.get_node() for child in self.ui_children]
        self._main_priority = max((_priority(child, 'x') for child in self.ui_children if child._visible), default=0)
        for i,child in enumerate(self.ui_children):
            child = child.get_node()
            self.ui_children[i] = child
            self.putChild(i, child)
        super().postSync()

class VBox(_BoxMixin, TkBaseWidget):
    expand_x_prio = 1
    expand_y_prio = 2
    pui_terminal = False

    ttk_style = "TFrame"
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui_children = prev.ui_children
            self.ui_gridmap = prev.ui_gridmap
        else:
            self.ui = ttk.Frame(self.tkparent.inner)
            self.ui.grid_columnconfigure(0, weight=1)
            self.ui_children = []
            self.ui_gridmap = set()
        super().update(prev)

    def addChild(self, idx, child):
        self.ui_children.insert(idx, child)

    def removeChild(self, idx, child):
        self.ui_children.pop(idx)
        if isinstance(child, TkBaseWidget):
            child_outer = child.outer
            if child_outer:
                child_outer.grid_forget()

    def putChild(self, idx, child):
        if isinstance(child, TkBaseWidget):
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            if not child._visible:
                child.outer.grid_remove()
                self.ui.grid_rowconfigure(idx, weight=0, uniform="")
                self.ui_gridmap.discard(idx)
                return
            weight, sticky = _linear_options(self, child, 'y')
            child.outer.grid(row=idx, column=0, sticky=sticky, padx=(left, right), pady=(top, bottom))
            self.ui.grid_rowconfigure(idx, weight=weight, uniform="." if child.layout_weight and weight else "")
            if weight:
                self.ui_gridmap.add(idx)
            else:
                self.ui_gridmap.discard(idx)

    def postSync(self):
        n = len(self.ui_children)
        tbd = []
        for i in self.ui_gridmap:
            if i >= n:
                self.ui.grid_rowconfigure(i, weight=0, uniform="")
                tbd.append(i)
        for i in tbd:
            self.ui_gridmap.discard(i)

        self.ui_children[:] = [child.get_node() for child in self.ui_children]
        self._main_priority = max((_priority(child, 'y') for child in self.ui_children if child._visible), default=0)
        for i,child in enumerate(self.ui_children):
            child = child.get_node()
            self.ui_children[i] = child
            self.putChild(i, child)
        super().postSync()

class Spacer(TkBaseWidget):
    ttk_style = "TFrame"
    def __init__(self, layout=None, side=None):
        super().__init__(layout, side)
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ttk.Frame(self.tkparent.inner)
        super().update(prev)


class Grid(GridMixin, TkBaseWidget):
    expand_x_prio = 1
    expand_y_prio = 1
    pui_terminal = False
    pui_grid_layout = True
    ttk_style = 'TFrame'

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.mounted, self.axes = prev.ui, prev.mounted, prev.axes
        else:
            self.ui = ttk.Frame(self.tkparent.inner)
            self.mounted, self.axes = [], (set(), set())
        super().update(prev)

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        child.outer.grid_forget()

    def postSync(self):
        rows, columns = self.axes
        for row in rows:
            self.ui.rowconfigure(row, weight=0)
        for column in columns:
            self.ui.columnconfigure(column, weight=0, uniform="")
        rows.clear()
        columns.clear()
        for child in self.mounted:
            if not child.get_node()._visible:
                child.get_node().outer.grid_remove()
        for child, (row, column, rowspan, columnspan) in self.grid_cells(self.mounted):
            if not child._visible:
                continue
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            child.outer.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan,
                             sticky=_sticky(child), padx=(left, right), pady=(top, bottom))
            rows.update(range(row, row + rowspan))
            columns.update(range(column, column + columnspan))
        columns.update(range(self._grid_columns or 0))
        for row in rows:
            self.ui.rowconfigure(row, weight=1)
        for column in columns:
            self.ui.columnconfigure(column, weight=1, uniform="pui-grid" if self._grid_columns else "")


class Stack(VBox):
    """One grid cell provides native overlap and maximum-child size negotiation."""
    expand_x_prio = 2
    expand_y_prio = 2

    def putChild(self, idx, child):
        if not child._visible:
            child.outer.grid_remove()
            return
        if isinstance(child, Spacer):
            return
        if isinstance(child, TkBaseWidget):
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            child.outer.grid(row=0, column=0, sticky='nsew',
                             padx=(left, right), pady=(top, bottom))
            child.outer.lift()

    def postSync(self):
        self.ui.grid_rowconfigure(0, weight=1)
        self.ui_children[:] = [child.get_node() for child in self.ui_children]
        for idx, child in enumerate(self.ui_children):
            self.putChild(idx, child)
        TkBaseWidget.postSync(self)


class _AdaptiveLayout(HBox):
    def update(self, prev):
        super().update(prev)
        if prev is None or self.container_x != prev.container_x:
            for i in range(max(len(self.ui_children), 1)):
                self.ui.grid_rowconfigure(i, weight=0, uniform="")
                self.ui.grid_columnconfigure(i, weight=0, uniform="")
            self.ui_gridmap.clear()
        if self.container_x:
            self.ui.grid_rowconfigure(0, weight=1)
        else:
            self.ui.grid_columnconfigure(0, weight=1)

    def putChild(self, idx, child):
        (HBox if self.container_x else VBox).putChild(self, idx, child)

    def postSync(self):
        configure = self.ui.grid_columnconfigure if self.container_x else self.ui.grid_rowconfigure
        for i in tuple(self.ui_gridmap):
            if i >= len(self.ui_children):
                configure(i, weight=0, uniform="")
                self.ui_gridmap.discard(i)
        self.ui_children[:] = [child.get_node() for child in self.ui_children]
        axis = 'x' if self.container_x else 'y'
        self._main_priority = max((_priority(child, axis) for child in self.ui_children if child._visible), default=0)
        for i, child in enumerate(self.ui_children):
            self.putChild(i, child)
        TkBaseWidget.postSync(self)


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
