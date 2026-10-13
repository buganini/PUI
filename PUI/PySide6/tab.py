from .. import *
from .base import *
from .layout import VBox
from ..selection import TabsMixin

class Tabs(TabsMixin, QtBaseWidget):
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
        else:
            self.ui = QtWidgets.QTabWidget()
            self.ui.currentChanged.connect(self._native_selected)
        positions = {self.NORTH: QtWidgets.QTabWidget.TabPosition.North,
                     self.SOUTH: QtWidgets.QTabWidget.TabPosition.South,
                     self.EAST: QtWidgets.QTabWidget.TabPosition.East,
                     self.WEST: QtWidgets.QTabWidget.TabPosition.West}
        self.ui.setTabPosition(positions[self.tabposition])
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        self.ui.insertTab(idx, child.outer, child.label)

    def removeChild(self, idx, child):
        self.ui.removeTab(idx)

    def postSync(self):
        for i,c in enumerate(self.children):
            self.ui.setTabText(i, c.label)
        super().postSync()

    def _show_tab(self, index):
        self.ui.setCurrentIndex(-1 if index is None else index)


class Tab(VBox):
    def __init__(self, label):
        super().__init__()
        self.label = label
        self.layout_padding = (0, 0, 0, 0)
