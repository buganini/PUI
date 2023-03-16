from .. import *
from .base import *

class QtWindowSignal(QtCore.QObject):
    redraw = QtCore.Signal()

class QtWindow(PUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size
        self.signal = QtWindowSignal()
        self.signal.redraw.connect(self.update)

    def redraw(self):
        self.signal.redraw.emit()

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

    def start(self):
        self.window.show()
        self.app.exec_()
