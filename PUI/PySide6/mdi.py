from .. import *
from .base import *

class MdiArea(QtBaseWidget):
    terminal = False
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QMdiArea()

        super().update(prev)

    def addChild(self, idx, child):
        self.ui.addSubWindow(child.outer)

    def removeChild(self, idx, child):
        self.ui.removeSubWindow(child.outer)

    def addSubWindow(self, child):
        self.ui.addSubWindow(child.outer)

    def removeSubWindow(self, child):
        self.ui.removeSubWindow(child.outer)

class MdiSubWindow(QtBaseFrame):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QMdiSubWindow()

        super().update(prev)
