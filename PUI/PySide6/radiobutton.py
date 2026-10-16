from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy

class RadioButton(QtBaseWidget):
    def __init__(self, text, value, model, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.clicked.disconnect()
        else:
            self.ui = QtWidgets.QRadioButton()
        self.ui.setText(self.text)
        self.ui.setChecked(self.model.value == self.value)
        self.ui.clicked.connect(self._clicked)
        self.ui.setEnabled(self.enabled)
        super().update(prev)

    def _clicked(self):
        self.model.value = self.value
        super()._clicked()
