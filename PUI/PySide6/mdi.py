from .. import *
from .base import *

class QtMdiArea(QtBaseWidget):
    terminal = False
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QMdiArea()

        super().update(prev)

    def addChild(self, idx, child):
        self.ui.addSubWindow(child.outer)

    def removeChild(self, idx, child):
        self.ui.removeSubWindow(child.outer)

class QtMdiSubWindow(QtBaseFrame):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QMdiSubWindow()

        super().update(prev)
