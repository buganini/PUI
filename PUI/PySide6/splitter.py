from .. import *
from .base import *

class QtSplitter(QtBaseWidget):
    terminal = False
    def __init__(self, vertical=False):
        super().__init__()
        self.vertical = vertical

    def destroy(self, direct):
        if direct:
            for frame in self.frame:
                if frame:
                    frame.deleteLater()
        super().destroy(direct)

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.frame = prev.frame
        else:
            self.ui = QtWidgets.QSplitter()
            self.frame = []
        self.ui.setOrientation(QtCore.Qt.Orientation.Vertical if self.vertical else QtCore.Qt.Orientation.Horizontal)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            frame = QtWidgets.QWidget()
            frame.setLayout(child.outer)
            self.frame.insert(idx, frame)
            self.ui.insertWidget(idx, frame)
        elif isinstance(child, QtBaseWidget):
            self.ui.insertWidget(idx, child.outer)
            self.frame.insert(idx, None)
        else:
            self.addChild(idx, child.children[0])
    
    def removeChild(self, idx, child):
        child.outer.setParent(None)
        frame = self.frame.pop(idx)
        if frame:
            frame.deleteLater()
