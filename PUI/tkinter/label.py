from .. import *
from .base import *
class TkLabel(TkBaseWidget):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.config(text = self.text)
        else:
            import tkinter as tk
            self.ui = tk.Label(self.parent.ui, text=self.text, **self.kwargs)
        return self.ui