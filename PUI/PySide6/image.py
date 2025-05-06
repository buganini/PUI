from .. import *
from .base import *
from .label import ClickableQLabel
from PySide6.QtWidgets import QSizePolicy
import os

class Image(QtBaseWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.pixmap = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.eventFilter = prev.eventFilter
            self.curr_path = prev.curr_path
            self.curr_path_mtime = prev.curr_path_mtime
            self.pixmap = prev.pixmap
        else:
            self.ui = ClickableQLabel()
            self.ui.clicked.connect(self._clicked)
            self.curr_path = Prop()
            self.curr_path_mtime = Prop()

        if self._onClicked:
            self.ui.setCursor(QtCore.Qt.PointingHandCursor)

        if self.layout_weight:
            # XXX keep aspect ratio
            self.ui.setScaledContents(True)
            self.ui.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored))
        else:
            self.ui.setScaledContents(False)
            self.ui.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred))

        if self.curr_path.set(self.path) or self.curr_path_mtime.set(os.path.getmtime(self.path)):
            self.pixmap = QtGui.QPixmap(self.path)
            if self.layout_width is not None and self.layout_height is not None:
                self.pixmap = self.pixmap.scaled(self.layout_width, self.layout_height, QtCore.Qt.KeepAspectRatio, mode=QtCore.Qt.SmoothTransformation)
            elif self.layout_width is not None:
                self.pixmap = self.pixmap.scaledToWidth(self.layout_width, mode=QtCore.Qt.SmoothTransformation)
            elif self.layout_height is not None:
                self.pixmap = self.pixmap.scaledToHeight(self.layout_height, mode=QtCore.Qt.SmoothTransformation)

            self.ui.setPixmap(self.pixmap)

        super().update(prev)
