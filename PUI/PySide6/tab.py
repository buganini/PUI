from .. import *
from .base import *

class Tabs(QtBaseWidget):
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
            self.ui = QtWidgets.QTabWidget()
        super().update(prev)

    def addChild(self, idx, child):
        parent = child.parent
        while not isinstance(parent, Tab):
            parent = parent.parent
        self.ui.insertTab(idx, child.outer, parent.label)

    def removeChild(self, idx, child):
        self.ui.removeTab(idx)

    def postSync(self):
        for i,c in enumerate(self.children):
            self.ui.setTabText(i, c.label)


class Tab(PUINode):
    pui_virtual = True
    def __init__(self, label):
        super().__init__()
        self.label = label
