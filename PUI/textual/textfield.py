from .. import *
from .base import *

class TInput(TBase):
    content_width = None
    def __init__(self, model):
        super().__init__()
        self.model = model

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            model_value = self.model.value
            if self.ui_text != model_value:
                self.ui_text = model_value
                self.ui.value = model_value
        else:
            self.ui_text = self.model.value
            self.ui = widgets.Input(self.ui_text)

        self.ui.puinode = self


    def _changed(self, value):
        self.ui_text = value
        self.model.value = value

    def _submitted(self, value):
        pass
