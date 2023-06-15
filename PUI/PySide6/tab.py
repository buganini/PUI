from .. import *
from .base import *

class QtTabWidget(QtBaseWidget):
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
            self.ui = QtWidgets.QTabWidget()
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, QtTab):
            raise RuntimeError("QtTabWidget can only contain QtTab")

        self._addChild(idx, child.children[0], child.label)

    def _addChild(self, idx, child, label):
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.insertTab(idx, child.outer, label)
        elif child.children:
            self._addChild(idx, child.children[0], label)

    def removeChild(self, idx, child):
        self.ui.removeTab(idx)


class QtTab(PUINode):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def addChild(self, idx, child):
        if idx > 0:
            raise RuntimeError("QtTab can only have one child")
