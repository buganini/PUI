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
            self.curr_path = Prop()

        if self.curr_path.set(self.path):
            self.pixmap = QtGui.QPixmap(self.path)
            if self.layout_width is not None and self.layout_height is not None:
                self.pixmap = self.pixmap.scaled(self.layout_width, self.layout_height, QtCore.Qt.KeepAspectRatio)
            elif self.layout_width is not None:
                self.pixmap = self.pixmap.scaledToWidth(self.layout_width)
            elif self.layout_height is not None:
                self.pixmap = self.pixmap.scaledToHeight(self.layout_height)

            self.ui.setPixmap(self.pixmap)

        super().update(prev)
