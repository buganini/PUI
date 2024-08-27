from .. import *
from .base import *

class Tabs(TkBaseWidget):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    pui_terminal = False
    def __init__(self, tabposition=NORTH):
        super().__init__()
        self.tabposition = tabposition

    def destroy(self, direct):
        if direct:
            for w in self.widgets:
                if w:
                    w.deleteLater()
        super().destroy(direct)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.childrenui = prev.childrenui
        else:
            self.ui = ttk.Notebook(self.tkparent.inner)
            self.childrenui = []
        super().update(prev)

    def addChild(self, idx, child):
        if idx < len(self.childrenui):
            self.ui.insert(self.childrenui[idx], child.outer, text=child.parent.label)
            self.childrenui.insert(idx, child.outer)
        else:
            self.ui.add(child.outer, text=child.parent.label)
            self.childrenui.append(child.outer)

    def removeChild(self, idx, child):
        self.ui.forget(child.outer)
        self.childrenui.pop(idx)

    def postSync(self):
        for i,c in enumerate(self.children):
            self.ui.tab(i, text=c.label)
        return super().postSync()

class Tab(PUINode):
    pui_virtual = True
    def __init__(self, label):
        super().__init__()
        self.label = label

