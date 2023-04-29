from .. import *
from .base import *

class QtWindow(PUINode):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    def update(self, prev=None):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            from PyQt5 import QtWidgets
            self.ui = QtWidgets.QWidget()
            self.ui.setObjectName("Window")
            self.box = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
            self.ui.setLayout(self.box)

        if not self.title is None:
            self.ui.setWindowTitle(self.title)
        if not self.size is None:
            self.ui.resize(*self.size)

        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.box.addLayout(child.ui)
        elif isinstance(child, QtBaseWidget):
            self.box.addWidget(child.ui)
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.box.removeItem(child.ui)
        elif isinstance(child, QtBaseWidget):
            child.ui.setParent(None)
        else:
            self.removeChild(idx, child.children[0])
