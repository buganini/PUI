from .. import *
from .base import *
class TkButton(TkBaseWidget):
    def __init__(self, text, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.callback = callback

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.config(text = self.text)
            self.ui.config(command = self.callback)
        else:
            self.ui = tk.Button(self.parent.ui, text=self.text, command=self.callback, **self.kwargs)
