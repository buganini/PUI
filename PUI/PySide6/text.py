from .. import *
from .base import *
from PySide6.QtWidgets import QSizePolicy

class QText(QtWidgets.QLabel):
    def __init__(self, text, sizeHint):
        self._sizehint = sizeHint
        super().__init__(text)

    def sizeHint(self):
        return QtCore.QSize(*self._sizehint)

    def minimumSizeHint(self):
        return QtCore.QSize(*self._sizehint)
    
    def setSizeHint(self, sizeHint):
        if sizeHint != self._sizehint:
            self._sizehint = sizeHint
            self.adjustSize()

class QtText(QtBaseWidget):
    def __init__(self, text, richtext=True, sizeHint=(120,320)):
        super().__init__()
        self.text = text
        self.richtext = richtext
        self.onClicked = None
        self.sizeHint = sizeHint

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.setSizeHint(self.sizeHint)
        else:
            self.ui = QText(self.text, self.sizeHint)
            self.ui.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.ui.setWordWrap(True)
            self.ui.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored))


        super().update(prev)
