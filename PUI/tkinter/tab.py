from .. import *
from .base import *
from .layout import VBox
from ..selection import TabsMixin

class Tabs(TabsMixin, TkBaseWidget):
    use_ttk = "TNotebook"
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    pui_terminal = False
    def __init__(self, tabposition=NORTH, model=None):
        super().__init__(model=model)
        if tabposition not in (self.NORTH, self.SOUTH, self.EAST, self.WEST):
            raise ValueError('Unknown tab position')
        self.tabposition = tabposition

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.childrenui = prev.childrenui
        else:
            self.ui = ttk.Notebook(self.tkparent.inner)
            self.ui.bind('<<NotebookTabChanged>>', self._tab_changed)
            self.childrenui = []
        super().update(prev)
        ttk.Style(self.ui).configure(self.ui.cget('style'), tabposition=self.tabposition)

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        if idx < len(self.childrenui):
            self.ui.insert(self.childrenui[idx], child.outer, text=child.label)
            self.childrenui.insert(idx, child.outer)
        else:
            self.ui.add(child.outer, text=child.label)
            self.childrenui.append(child.outer)

    def removeChild(self, idx, child):
        self.ui.forget(child.outer)
        self.childrenui.pop(idx)

    def postSync(self):
        for i,c in enumerate(self.children):
            self.ui.tab(i, text=c.label)
        return super().postSync()

    def _show_tab(self, index):
        if index is not None:
            self.ui.select(index)

    def _tab_changed(self, event):
        node = self.get_node()
        if not node.destroyed and node.ui is not None and node.ui.select():
            node._native_selected(node.ui.index(node.ui.select()))


class Tab(VBox):
    def __init__(self, label):
        super().__init__()
        self.label = label
        self.layout_padding = (0, 0, 0, 0)

