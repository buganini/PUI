from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *


class _ContentButton(QtWidgets.QPushButton):
    def sizeHint(self):
        size = super().sizeHint()
        # Keep native sizing for icons/menus added through Qt interop.
        if not self.icon().isNull() or self.menu() is not None:
            return size
        option = QtWidgets.QStyleOptionButton()
        self.initStyleOption(option)
        content = self.fontMetrics().size(QtCore.Qt.TextFlag.TextShowMnemonic, option.text)
        # Some styles impose a standard button width whenever text is present.
        # Supply its measured size separately, keeping theme padding and borders
        # without that width floor. The native height and painting stay intact.
        option.text = ''
        fitted = self.style().sizeFromContents(QtWidgets.QStyle.ContentsType.CT_PushButton,
                                             option, content, self)
        size.setWidth(fitted.width())
        return size


class Button(QtBaseWidget):
    def __init__(self, text: _t.Any, *, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.disabled = disabled
        self._tag = self.text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.clicked.disconnect()
        else:
            self.ui = _ContentButton(text=self.text)
        self.ui.clicked.connect(self._clicked)
        self.ui.setDisabled(self.disabled)
        super().update(prev)
