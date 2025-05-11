from .. import *
from .base import *

class TextField(FBase):
    def __init__(self, model, edit_model=None, label="", **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.label = label
        self.edit_model = edit_model
        self.editing = False

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
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
            self.ui = ft.TextField(label=self.label, value=model_value, on_change=self.on_textbox_changed, on_blur=self.on_blur, on_submit=self.on_submit, expand=self.layout_weight)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_textbox_changed(self, e): # editing
        node = self.get_node()
        node.editing = True
        value = e.control.value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)

    def on_change(self, e): # finish editing
        node = self.get_node()
        node.editing = False
        value = e.control.value
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._change(e)

    def on_blur(self, e):
        self.on_change(e)

    def on_submit(self, e):
        self.on_change(e)
