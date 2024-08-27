from .. import *
from .base import *

class Tabs(FBase):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    pui_terminal = False
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
        tab = ft.Tab(text=child.parent.label, content=child.outer)
        self.ui.tabs.insert(idx, tab)

    def removeChild(self, idx, child):
        self.ui.tabs.pop(idx)

    def postSync(self):
        for i,c in enumerate(self.children):
            self.ui.tabs[i].text = c.label
        try:
            self.ui.update()
        except:
            pass
        return super().postSync()


class Tab(PUINode):
    pui_virtual = True
    def __init__(self, label):
        super().__init__()
        self.label = label
