from .. import *
from .base import *

class QtLabel(QtBaseWidget):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
        else:
            self.ui = QtWidgets.QLabel(self.text)
