from .. import *
from .base import *

class Button(TBase):
    def __init__(self, text, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.label = self.text
        else:
            self.ui = widgets.Button(self.text)
        self.ui.puinode = self
        self.ui.disabled = not self.enabled
        super().update(prev)
