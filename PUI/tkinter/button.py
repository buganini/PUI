from .. import *
from .base import *
class Button(TkBaseWidget):
    def __init__(self, text, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.config(text = self.text)
            self.ui.config(command = self._clicked)
        else:
            self.ui = tk.Button(self.tkparent.inner, text=self.text, command=self._clicked)
        self.ui.configure(state='normal' if self.enabled else 'disabled')
        super().update(prev)
