from .. import *
from .base import *
from .menu import *

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
            self.frame = prev.frame
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
        else:
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QMainWindow()
            self.frame = None

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
        if isinstance(child, QtMenuBar):
            self.ui.setMenuBar(child.outer)
        elif isinstance(child, QtBaseLayout):
            self.frame = QtWidgets.QWidget()
            self.ui.setCentralWidget(self.frame)
            self.frame.setLayout(child.outer)
        elif isinstance(child, QtBaseWidget):
            self.ui.setCentralWidget(child.outer)
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, QtMenuBar):
            child.outer.close()
        elif isinstance(child, QtBaseLayout):
            self.frame.setParent(None)
            self.frame.deleteLater()
            self.frame = None
        elif isinstance(child, QtBaseWidget):
            child.outer.setParent(None)
        else:
            self.removeChild(idx, child.children[0])
