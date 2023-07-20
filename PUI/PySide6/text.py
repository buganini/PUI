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

class Text(QtBaseWidget):
    textformat = QtCore.Qt.TextFormat.PlainText
    def __init__(self, text, selectable=False, sizeHint=(120,320)):
        super().__init__()
        self.text = text
        self.selectable = selectable
        self.sizeHint = sizeHint

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.setSizeHint(self.sizeHint)
        else:
            self.ui = QText(self.text, self.sizeHint)
            self.ui.setTextFormat(self.textformat)
            self.ui.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.ui.setWordWrap(True)
            self.ui.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored))

        if self.selectable:
            self.ui.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        else:
            self.ui.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        super().update(prev)


class Html(Text):
    textformat = QtCore.Qt.TextFormat.RichText

class MarkDown(Text):
    textformat = QtCore.Qt.TextFormat.MarkdownText
