from .. import *
from .base import *

class TextField(TBase):
    content_width = None
    def __init__(self, model):
        super().__init__()
        self.model = model

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_text = prev.curr_text

            if self.curr_text.set(model_value):
                self.ui.value = model_value
        else:
            self.ui = widgets.Input(model_value)
            self.curr_text = Prop(model_value)

        self.ui.puinode = self
        super().update(prev)


    def _changed(self, value):
        self.ui_text = value
        self.model.value = value

    def _submitted(self, value):
        pass
