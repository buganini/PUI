from .. import *
from .base import *

class QtApplication(QPUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size
        self.app = None

    def update(self, prev=None):
        if not self.app:
            from PyQt5 import QtWidgets
            self.app = QtWidgets.QApplication([])

        super().update(prev)

    def addChild(self, idx, child):
        child.ui.show()

    def removeChild(self, idx, child):
        child.ui.close()

    def start(self):
        self.app.exec_()
