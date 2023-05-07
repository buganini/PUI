from .. import *
from .base import *

class QtButton(QtBaseWidget):
    def __init__(self, text, callback=None, *cb_args, **cb_kwargs):
        super().__init__()
        self.text = text
        self.callback = callback
        self.cb_args = cb_args
        self.cb_kwargs = cb_kwargs

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
            try:
                self.ui.clicked.disconnect()
            except:
                pass
            self.ui.clicked.connect(self._clicked)
            prev.callback = None
        else:
            self.ui = QtWidgets.QPushButton(text=self.text)
            self.ui.clicked.connect(self._clicked)
        super().update(prev)

    def _clicked(self):
        if self.callback:
            self.callback(*self.cb_args, **self.cb_kwargs)
