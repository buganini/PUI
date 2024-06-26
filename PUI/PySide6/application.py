from .. import *
from .base import *

class Application(QtPUIView):
    def __init__(self, icon=None):
        super().__init__()
        self.ui = None
        self.icon = icon

    def redraw(self):
        self.update(None)

    def update(self, prev=None):
        if not self.ui:
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QApplication([])
            if self.icon:
                self.ui.setWindowIcon(QtGui.QIcon(self.icon))

        super().update(prev)

    def addChild(self, idx, child):
        child.outer.show()

    def removeChild(self, idx, child):
        child.outer.close()

    def start(self):
        self.ui.exec()
