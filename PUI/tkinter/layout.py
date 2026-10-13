from .. import *
from .base import *


def _sticky(child):
    return getattr(child, 'grid_sticky', 'nsew')

class HBox(TkBaseWidget):
    pui_terminal = False

    use_ttk = "TFrame"
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
            child.outer.grid(row=0, column=idx, sticky=_sticky(child), padx=(left, right), pady=(top, bottom))
            if child.layout_weight is None:
                weight = getattr(child, 'grid_weight_x', 0)
                self.ui.grid_columnconfigure(idx, weight=weight, uniform="" if not weight else ".")
                if weight:
                    self.ui_gridmap.add(idx)
                else:
                    self.ui_gridmap.discard(idx)
            else:
                self.ui.grid_columnconfigure(idx, weight=child.layout_weight, uniform=".")
                self.ui_gridmap.add(idx)

    def postSync(self):
        n = len(self.ui_children)
        tbd = []
        for i in self.ui_gridmap:
            if i >= n:
                self.ui.grid_columnconfigure(i, weight=0, uniform="")
                tbd.append(i)
        for i in tbd:
            self.ui_gridmap.discard(i)

        for i,child in enumerate(self.ui_children):
            child = child.get_node()
            self.ui_children[i] = child
            self.putChild(i, child)
        super().postSync()

class VBox(TkBaseWidget):
    pui_terminal = False

    use_ttk = "TFrame"
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
            child.outer.grid(row=idx, column=0, sticky=_sticky(child), padx=(left, right), pady=(top, bottom))
            if child.layout_weight is None:
                weight = getattr(child, 'grid_weight_y', 0)
                self.ui.grid_rowconfigure(idx, weight=weight, uniform="" if not weight else ".")
                if weight:
                    self.ui_gridmap.add(idx)
                else:
                    self.ui_gridmap.discard(idx)
            else:
                self.ui.grid_rowconfigure(idx, weight=child.layout_weight, uniform=".")
                self.ui_gridmap.add(idx)

    def postSync(self):
        n = len(self.ui_children)
        tbd = []
        for i in self.ui_gridmap:
            if i >= n:
                self.ui.grid_rowconfigure(i, weight=0, uniform="")
                tbd.append(i)
        for i in tbd:
            self.ui_gridmap.discard(i)

        for i,child in enumerate(self.ui_children):
            child = child.get_node()
            self.ui_children[i] = child
            self.putChild(i, child)
        super().postSync()

class Spacer(TkBaseWidget):
    use_ttk = "TFrame"
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
    pui_terminal = False
    pui_grid_layout = True
    use_ttk = 'TFrame'

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
