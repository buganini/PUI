from .. import *
from .base import *

class TText(TBase):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.update(self.text)
        else:
            self.ui = widgets.Label(self.text, markup=False)
