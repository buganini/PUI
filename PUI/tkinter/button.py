from .. import *
from .base import *
class TkButton(TkBaseWidget):
    def __init__(self, text, callback=None, *cb_args, **cb_kwargs):
        super().__init__()
        self.text = text
        self.callback = callback
        self.cb_args = cb_args
        self.cb_kwargs = cb_kwargs

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.config(text = self.text)
            self.ui.config(command = self._callback)
        else:
            self.ui = tk.Button(self.parent.ui, text=self.text, command=self._callback, **self.kwargs)

    def _callback(self):
        if self.callback:
            self.callback(*self.cb_args, **self.cb_kwargs)