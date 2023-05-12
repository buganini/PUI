from .. import *
from .base import *

class QtWindow(QtBaseWidget):
    terminal = False

    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None

    def update(self, prev=None):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
        else:
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QWidget()
            self.ui.setObjectName("Window")
            self.box = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
            self.ui.setLayout(self.box)

        if self.curr_size != self.size:
            self.curr_size = self.size
            self.ui.resize(*self.size)
        if self.curr_maximize !=  self.maximize:
            self.curr_maximize = self.maximize
            self.ui.showMaximized()
        if self.curr_fullscreen != self.fullscreen:
            self.curr_fullscreen = self.fullscreen
            self.ui.showFullScreen()
        if not self.title is None:
            self.ui.setWindowTitle(self.title)
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
