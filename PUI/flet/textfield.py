from .. import *
from .base import *

class TextField(FBase):
    def __init__(self, model, label="", **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.label = label

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if self.curr_value.set(model_value):
                self.ui.value = model_value
                try:
                    self.ui.update()
                except:
                    pass
        else:
            self.curr_value = Prop(model_value)
            self.ui = ft.TextField(label=self.label, value=model_value, on_change=self.on_textbox_changed, expand=self.layout_weight)
        super().update(prev)

    def on_textbox_changed(self, e):
        self.model.value = e.control.value
