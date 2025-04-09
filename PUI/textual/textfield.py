from .. import *
from .base import *

class TextField(TBase):
    content_width = None
    def __init__(self, model, edit_model=None):
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.editing = False

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value

            if self.curr_value.set(model_value) and not self.editing:
                self.ui.value = model_value
        else:
            self.ui = widgets.Input(model_value)
            self.curr_value = Prop(model_value)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        self.ui.puinode = self
        super().update(prev)


    def _changed(self, value):
        node = self.get_node()
        if node.edit_model:
            node.editing = True
            node.edit_model.value = value
        else:
            node.model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)

    def _submitted(self, value):
        node = self.get_node()
        node.editing = False
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._change(e)