from .. import *
from .base import *

class TCheckbox(TBase):
    def __init__(self, text, model):
        super().__init__()
        self.text = text
        self.model = model

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.value = self.model.value
        else:
            self.ui = widgets.Checkbox(self.text, self.model.value)

        self.ui.puinode = self
        super().update(prev)

    def _changed(self, value):
        self.model.value = value
