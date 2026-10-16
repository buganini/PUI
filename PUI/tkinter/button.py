from .. import *
from .base import *
class Button(TkBaseWidget):
    ttk_style = "TButton"
    def __init__(self, text, *, disabled=False):
        super().__init__()
        self.text = text
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.config(text = self.text)
            self.ui.config(command = self._clicked)
        else:
            self.ui = ttk.Button(self.tkparent.inner, text=self.text, command=self._clicked)
        self.ui.configure(state='disabled' if self.disabled else 'normal')
        super().update(prev)
