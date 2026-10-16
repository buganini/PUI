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


class HBox(TkBaseWidget):
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
        self._main_priority = max((_priority(child, 'x') for child in self.ui_children), default=0)
        for i,child in enumerate(self.ui_children):
            child = child.get_node()
            self.ui_children[i] = child
            self.putChild(i, child)
        super().postSync()

class VBox(TkBaseWidget):
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
        self._main_priority = max((_priority(child, 'y') for child in self.ui_children), default=0)
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


class Grid(TkBaseWidget):
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
            self.ui.columnconfigure(column, weight=0)
        rows.clear()
        columns.clear()
        for i, child in enumerate(self.mounted):
            child = child.get_node()
            self.mounted[i] = child
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            rowspan, columnspan = child.grid_rowspan or 1, child.grid_columnspan or 1
            child.outer.grid(row=child.grid_row, column=child.grid_column,
                             rowspan=rowspan, columnspan=columnspan,
                             sticky=_sticky(child), padx=(left, right), pady=(top, bottom))
            rows.update(range(child.grid_row, child.grid_row + rowspan))
            columns.update(range(child.grid_column, child.grid_column + columnspan))
        for row in rows:
            self.ui.rowconfigure(row, weight=1)
        for column in columns:
            self.ui.columnconfigure(column, weight=1)
