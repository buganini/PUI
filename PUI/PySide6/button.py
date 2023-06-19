from .. import *
from .base import *

class Button(QtBaseWidget):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
            try:
                self.ui.clicked.disconnect()
            except:
                pass
            prev.callback = None
        else:
            self.ui = QtWidgets.QPushButton(text=self.text)
        self.ui.clicked.connect(self._clicked)
        super().update(prev)
