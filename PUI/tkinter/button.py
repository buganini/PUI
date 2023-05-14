from .. import *
from .base import *
class TkButton(TkBaseWidget):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.config(text = self.text)
            self.ui.config(command = self._clicked)
        else:
            self.ui = tk.Button(self.parent.ui, text=self.text, command=self._clicked, **self.kwargs)
