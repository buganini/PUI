from __future__ import annotations
from .. import _typing as _t
from ..common import Side
from .. import *
from .base import *
from .layout import VBox
from ..selection import TabsMixin

class Tabs(TabsMixin, QtBaseWidget):
    expand_x_prio = expand_y_prio = 3
    pui_terminal = False
    def __init__(self, tabposition: Side = Side.Top, model: _t.Binding[_t.Any] | None = None) -> None:
        super().__init__(model=model)
        if not isinstance(tabposition, Side):
            raise TypeError('tabposition must be a Side')
        self.tabposition = tabposition

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QTabWidget()
        positions = {Side.Top: QtWidgets.QTabWidget.TabPosition.North,
                     Side.Bottom: QtWidgets.QTabWidget.TabPosition.South,
                     Side.Right: QtWidgets.QTabWidget.TabPosition.East,
                     Side.Left: QtWidgets.QTabWidget.TabPosition.West}
        self.ui.setTabPosition(positions[self.tabposition])
        super().update(prev)
        if prev is not None:
            QtCore.QObject.disconnect(prev._selection_connection)
        self._selection_connection = self.ui.currentChanged.connect(self._native_selected)

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
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
