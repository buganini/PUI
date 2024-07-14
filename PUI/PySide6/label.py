from .. import *
from .base import *

class ClickableQLabel(QtWidgets.QLabel):
    clicked  = QtCore.Signal()

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)

class Label(QtBaseWidget):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = str(text)
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
        else:
            self.ui = ClickableQLabel(self.text)
            self.ui.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            self.ui.clicked.connect(self._clicked)
        if self._onClicked:
            self.ui.setCursor(QtCore.Qt.PointingHandCursor)

        if self.selectable:
            self.ui.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        else:
            self.ui.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        super().update(prev)
