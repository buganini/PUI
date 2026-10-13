from .. import *
from .base import *

class Button(QtBaseWidget):
    def __init__(self, text, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled
        self._tag = self.text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.clicked.disconnect()
        else:
            self.ui = QtWidgets.QPushButton(text=self.text)
        self.ui.clicked.connect(self._clicked)
        self.ui.setEnabled(self.enabled)
        super().update(prev)
