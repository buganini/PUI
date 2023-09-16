from .. import *
from .base import *

class Application(QtPUIView):
    def __init__(self):
        super().__init__()
        self.ui = None

    def update(self, prev=None):
        if not self.ui:
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QApplication([])

        super().update(prev)

    def addChild(self, idx, child):
        child.outer.show()

    def removeChild(self, idx, child):
        child.outer.close()

    def start(self):
        self.ui.exec()
