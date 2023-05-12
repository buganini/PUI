from .. import *
from .base import *

class ClickableQLabel(QtWidgets.QLabel):
    clicked  = QtCore.Signal()

    def mousePressEvent(self, ev):
        self.clicked.emit()

class QtLabel(QtBaseWidget):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.onClicked = None

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
        else:
            self.ui = ClickableQLabel(self.text)
            self.ui.clicked.connect(self._clicked)
        if self.onClicked:
            self.ui.setCursor(QtCore.Qt.PointingHandCursor)

        super().update(prev)

    def _clicked(self):
        node = self
        while node.retired_by:
            node = node.retired_by
        if node.onClicked:
            node.onClicked(*self.click_args, **self.click_kwargs)

    def click(self, callback, *cb_args, **cb_kwargs):
        self.onClicked = callback
        self.click_args = cb_args
        self.click_kwargs = cb_kwargs
