from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

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
            self.ui = QtWidgets.QPushButton(text=self.text)
        self.ui.clicked.connect(self._clicked)
        self.ui.setDisabled(self.disabled)
        super().update(prev)
