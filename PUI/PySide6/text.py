from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy
from .._url import OpenURL

class Text(QtBaseWidget):
    textformat = QtCore.Qt.TextFormat.PlainText
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
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
    expand_x_prio = expand_y_prio = 4
    textformat = QtCore.Qt.TextFormat.RichText

    def __init__(self, text, selectable=False, *, openURL=True):
        super().__init__(text, selectable)
        self.openURL = bool(openURL)

    def update(self, prev):
        creating = not (prev and prev.ui)
        super().update(prev)
        self.ui._pui_html = self
        self.ui.setOpenExternalLinks(False)
        if creating:
            self.ui.linkActivated.connect(lambda url, ui=self.ui: ui._pui_html._open_link(url))
        flags = self.ui.textInteractionFlags()
        if self.openURL:
            flags |= (QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse |
                      QtCore.Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
        self.ui.setTextInteractionFlags(flags)

    def _open_link(self, url):
        if self.openURL:
            OpenURL(url)

class MarkDown(Text):
    textformat = QtCore.Qt.TextFormat.MarkdownText
