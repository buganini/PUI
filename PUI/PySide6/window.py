from .. import *
from .base import *

class QtWindow(PUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    def update(self):
        if not hasattr(self, "window"):
            from PySide6 import QtWidgets
            self.app = QtWidgets.QApplication([])
            self.window = QtWidgets.QWidget()
            self.window.setObjectName("Window")
            self.box = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
            self.window.setLayout(self.box)

        if not self.title is None:
            self.window.setWindowTitle(self.title)
        if not self.size is None:
            self.window.resize(*self.size)

        super().update()

    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.box.addLayout(child.ui)
        else:
            self.box.addWidget(child.ui)

    def removeChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.box.removeItem(child.ui)
        else:
            child.ui.setParent(None)

    def start(self):
        self.window.show()
        self.app.exec_()
