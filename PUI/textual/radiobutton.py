from .. import *
from .base import *

class RadioButton(TBase):
    def __init__(self, text, value, model):
        super().__init__()
        self.text = text
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.RadioButton(self.text)
        self.ui.puinode = self
        self.ui.value = self.value  == self.model.value
        super().update(prev)

    def _changed(self, value):
        if value:
            self.model.value = self.value
        else:
            self.root.redraw()