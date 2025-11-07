from .. import *
from .base import *

class Stack(QtBaseLayout):
    pui_terminal = False
    pui_reversed_order = True

    def __init__(self):
        super().__init__()
        self.qt_params = {}
        if not isinstance(self.non_virtual_parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

    @property
    def outer(self):
        return self.ui

    @property
    def inner(self):
        return self.layout

    def destroy(self, direct):
        self.layout = None
        super().destroy(direct)

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qtlayout = prev.qtlayout
        else:
            self.ui = QtWidgets.QWidget()
            self.qtlayout = QtWidgets.QStackedLayout()
            self.qtlayout.setStackingMode(QtWidgets.QStackedLayout.StackAll)
            self.qtlayout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.qtlayout)
        super().update(prev)

    def addChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            pass
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.qtlayout.insertWidget(idx, child.outer)
            self.mounted_children.insert(idx, child)

    def removeChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            pass
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
            self.mounted_children.pop(idx)

    def postUpdate(self):
        if self.ui:
            if self._onDropped:
                self.ui.setAcceptDrops(True)
                self.ui.installEventFilter(self.eventFilter)
            else:
                self.ui.setAcceptDrops(False)

        super().postUpdate()

class HBox(QtBaseLayout):
    container_x = True
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
    container_y = True
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
    pui_movable = False

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