from .. import *
from .base import *

class QtLineEdit(QtBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def update(self, prev):
        value = self.model.value
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            if prev.last_value != value:
                self.ui.setText(str(value))
            self.last_value = value
        else:
            self.last_value = value
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QLineEdit()
            self.ui.setText(str(value))
            self.ui.textChanged.connect(self.on_textchanged)
        return self.ui

    def on_textchanged(self):
        self.model.value = self.ui.text()
