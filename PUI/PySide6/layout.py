from .. import *
from .base import *

class HBox(QtBaseLayout):
    def __init__(self):
        super().__init__()
        if not isinstance(self.parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.layout = prev.layout
        else:
            self.ui = QtWidgets.QWidget()
            self.layout = QtWidgets.QHBoxLayout()
            self.layout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.layout)
        super().update(prev)

class VBox(QtBaseLayout):
    def __init__(self):
        super().__init__()
        if not isinstance(self.parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.layout = prev.layout
        else:
            self.ui = QtWidgets.QWidget()
            self.layout = QtWidgets.QVBoxLayout()
            self.layout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.layout)
        super().update(prev)

class Spacer(PUINode):
    terminal = True

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            if isinstance(self.parent, VBox):
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
            elif isinstance(self.parent, HBox):
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            else:
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        super().update(prev)

    def destroy(self, direct):
        # self.ui.deleteLater() # QSpacerItem doesn't have .deleteLater()
        self.ui = None
        super().destroy(direct)

class Grid(QtBaseLayout):
    grid_layout = True
    def __init__(self):
        super().__init__()
        if not isinstance(self.parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

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