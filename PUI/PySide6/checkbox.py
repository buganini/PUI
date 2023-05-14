from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy

class QtCheckbox(QtBaseWidget):
    def __init__(self, text, model):
        super().__init__()
        self.text = text
        self.model = model

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            try:
                self.ui.stateChanged.disconnect()
            except:
                pass
        else:
            self.ui = QtWidgets.QCheckBox()
        self.ui.setText(self.text)
        self.ui.setChecked(bool(self.model.value))
        self.ui.stateChanged.connect(self._stateChanged)
        super().update(prev)

    def _stateChanged(self, value):
        self.model.value = bool(value)
