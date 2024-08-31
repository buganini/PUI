from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy

class Text(QtBaseWidget):
    textformat = QtCore.Qt.TextFormat.PlainText
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = str(text)
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
        else:
            self.ui = QtWidgets.QLabel(self.text)
            self.ui.setTextFormat(self.textformat)
            self.ui.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.ui.setWordWrap(True)

        if self.selectable:
            self.ui.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        else:
            self.ui.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        super().update(prev)


class Html(Text):
    textformat = QtCore.Qt.TextFormat.RichText

class MarkDown(Text):
    textformat = QtCore.Qt.TextFormat.MarkdownText
