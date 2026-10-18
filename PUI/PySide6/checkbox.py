from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy

class Checkbox(QtBaseWidget):
    def __init__(
        self,
        text: _t.Any,
        model: _t.Binding[_t.Any],
        value: _t.Any = None,
        *,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self.text = text
        self.disabled = disabled
        self.model = model
        self.value = text if value is None else value

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.stateChanged.disconnect()
            self.ui.clicked.disconnect()
        else:
            self.ui = QtWidgets.QCheckBox()
        self.ui.setText(self.text)
        self.ui.setChecked(checkbox_get(self.model, self.value))
        self.ui.stateChanged.connect(self._stateChanged)
        self.ui.clicked.connect(self._clicked)
        self.ui.setDisabled(self.disabled)
        super().update(prev)

    def _stateChanged(self, value):
        checkbox_set(self.model, bool(value), self.value)
