from .. import *
from .base import *

class UText(UBase):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.set_text(self.text)
        else:
            self.ui = urwid.Text(self.text)
