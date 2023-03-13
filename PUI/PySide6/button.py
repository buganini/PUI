from .. import *
from .base import *

class QtButton(QtBaseWidget):
    def __init__(self, text, callback=None):
        super().__init__()
        self.text = text
        self.callback = callback

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.clicked.disconnect()
            self.ui.clicked.connect(self.callback)
        else:
            self.ui = QtWidgets.QPushButton(text=self.text)
            self.ui.clicked.connect(self.callback)
        return self.ui