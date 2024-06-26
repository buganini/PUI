from .. import *
from .base import *

class Image(QtBaseWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.pixmap = None
        self.pixmap_path = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QLabel()

        if self.pixmap_path != self.path:
            self.pixmap = QtGui.QPixmap(self.path)
            self.pixmap_path = self.path
            self.ui.setPixmap(self.pixmap)

        super().update(prev)
