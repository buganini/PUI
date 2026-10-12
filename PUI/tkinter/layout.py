from .. import *
from .base import *

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
            child.outer.grid(row=0, column=idx, sticky='nsew', padx=(left, right), pady=(top, bottom))
            if child.layout_weight is None:
                self.ui.grid_columnconfigure(idx, weight=0, uniform="")
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
            child.outer.grid(row=idx, column=0, sticky='nsew', padx=(left, right), pady=(top, bottom))
            if child.layout_weight is None:
                self.ui.grid_rowconfigure(idx, weight=0, uniform="")
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
    def __init__(self, *args):
        super().__init__(*args)
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ttk.Frame(self.tkparent.inner)
        super().update(prev)
