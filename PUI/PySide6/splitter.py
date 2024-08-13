from .. import *
from .base import *

class Splitter(QtBaseWidget):
    pui_terminal = False
    def __init__(self, vertical=False):
        super().__init__()
        self.vertical = vertical

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QSplitter()
        self.ui.setOrientation(QtCore.Qt.Orientation.Vertical if self.vertical else QtCore.Qt.Orientation.Horizontal)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.insertWidget(idx, child.outer)
        else:
            self.addChild(idx, child.children[0])
    
    def removeChild(self, idx, child):
        child.outer.setParent(None)
