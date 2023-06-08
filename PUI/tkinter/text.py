from .. import *
from .base import *

class TkText(TkBaseWidget):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.config(text = self.text)
        else:
            self.ui = tk.Label(self.tkparent.inner, text=self.text, anchor="w", justify="left")
