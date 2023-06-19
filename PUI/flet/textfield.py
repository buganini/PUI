from .. import *
from .base import *

class TextField(FBase):
    def __init__(self, model, label="", **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.label = label

    def update(self, prev):
        value = self.model.value
        if prev and prev.ui:
            self.ui = prev.ui
            if prev.last_value != value:
                self.ui.value = str(value)
                try:
                    self.ui.update()
                except:
                    pass
            self.last_value = value
        else:
            self.last_value = value
            self.ui = ft.TextField(label=self.label, value=value, on_change=self.on_textbox_changed, expand=self.layout_weight)
        super().update(prev)

    def on_textbox_changed(self, e):
        self.model.value = e.control.value
