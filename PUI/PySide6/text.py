from .. import *
from .base import *
from ..utils import *
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
    textformat = QtCore.Qt.TextFormat.PlainText
    def __init__(self, text, sizeHint=(120,320)):
        super().__init__()
        self.text = text
        self.sizeHint = sizeHint

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.setSizeHint(self.sizeHint)
        else:
            self.ui = QText(self.text, self.sizeHint)
            self.ui.setTextFormat(self.textformat)
            self.ui.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.ui.setWordWrap(True)
            self.ui.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored))
        if self.layout_padding:
            self.ui.setContentsMargins(*trbl2ltrb(self.layout_padding))

        super().update(prev)


class QtHtml(QtText):
    textformat = QtCore.Qt.TextFormat.RichText

class QtMarkDown(QtText):
    textformat = QtCore.Qt.TextFormat.MarkdownText
