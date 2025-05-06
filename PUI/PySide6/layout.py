from .. import *
from .base import *

class HBox(QtBaseLayout):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qtlayout = prev.qtlayout
        else:
            self.ui = QtWidgets.QWidget()
            self.qtlayout = QtWidgets.QHBoxLayout()
            self.qtlayout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.qtlayout)
        super().update(prev)

class VBox(QtBaseLayout):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qtlayout = prev.qtlayout
        else:
            self.ui = QtWidgets.QWidget()
            self.qtlayout = QtWidgets.QVBoxLayout()
            self.qtlayout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.qtlayout)
        super().update(prev)

class Spacer(PUINode):
    pui_terminal = True

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            if isinstance(self.non_virtual_parent, VBox):
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
            elif isinstance(self.non_virtual_parent, HBox):
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            else:
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        super().update(prev)

    def destroy(self, direct):
        # self.ui.deleteLater() # QSpacerItem doesn't have .deleteLater()
        self.ui = None
        super().destroy(direct)

class Grid(QtBaseLayout):
    pui_grid_layout = True

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.layout = prev.layout
        else:
            self.ui = QtWidgets.QWidget()
            self.layout = QtWidgets.QGridLayout()
            self.layout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.layout)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.layout.addWidget(child.outer, child.grid_row, child.grid_column, child.grid_rowspan or 1, child.grid_columnspan or 1)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])