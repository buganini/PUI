from .. import *
from .base import *

class QtApplication(QPUIView):
    def __init__(self):
        super().__init__()
        self.app = None

    def update(self, prev=None):
        if not self.app:
            from PySide6 import QtWidgets
            self.app = QtWidgets.QApplication([])

        super().update(prev)

    def addChild(self, idx, child):
        child.ui.show()

    def removeChild(self, idx, child):
        child.ui.close()

    def start(self):
        self.app.exec_()
