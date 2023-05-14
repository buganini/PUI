from .. import *
from .base import *
from ..utils import *
from PySide6.QtWidgets import QSizePolicy

class QtRadioButton(QtBaseWidget):
    textformat = QtCore.Qt.TextFormat.PlainText
    def __init__(self, text, value, model):
        super().__init__()
        self.text = text
        self.value = value
        self.model = model
        self.onClicked = None

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            try:
                self.ui.clicked.disconnect()
            except:
                pass
        else:
            self.ui = QtWidgets.QRadioButton()
        self.ui.setText(self.text)
        self.ui.setChecked(self.model.value == self.value)
        self.ui.clicked.connect(self._clicked)
        super().update(prev)

    def _clicked(self):
        self.model.value = self.value
