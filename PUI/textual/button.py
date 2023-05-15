from .. import *
from .base import *

class TButton(TBase):
    def __init__(self, text, callback=None):
        super().__init__()
        self.text = text
        self.callback = callback

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.label = self.text
        else:
            self.ui = widgets.Button(self.text)
        self.ui.puinode = self
