from .. import *
from .base import *

class Image(QtBaseWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.pixmap = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_path = prev.curr_path
            self.pixmap = prev.pixmap
        else:
            self.ui = QtWidgets.QLabel()
            self.curr_path = Prop(None)

        if self.curr_path.set(self.path):
            self.pixmap = QtGui.QPixmap(self.path)
            self.ui.setPixmap(self.pixmap)

        super().update(prev)
