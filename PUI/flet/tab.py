from .. import *
from .base import *

class Tabs(FBase):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    terminal = False
    def __init__(self, tabposition=NORTH):
        super().__init__()
        self.tabposition = tabposition

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ft.Tabs(tabs=[], expand=1)
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise RuntimeError("Tabs can only contain Tab")

        tab = ft.Tab(text=child.label, content=child.children[0].outer)
        self.ui.tabs.insert(idx, tab)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.tabs.pop(idx)
        try:
            self.ui.update()
        except:
            pass


class Tab(PUINode):
    def __init__(self, label):
        super().__init__()
        self.label = label
