from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy

class Checkbox(QtBaseWidget):
    def __init__(self, text, model, value=None, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled
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
        self.ui.setEnabled(self.enabled)
        super().update(prev)

    def _stateChanged(self, value):
        checkbox_set(self.model, bool(value), self.value)
