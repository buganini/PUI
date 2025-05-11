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
            self.changing = prev.changing

            if self.curr_value.set(model_value) and not self.editing:
                self.changing = True # block changed event from next line
                self.ui.value = model_value
        else:
            self.ui = widgets.Input(model_value)
            self.curr_value = Prop(model_value)
            self.changing = True # block changed event from initialization

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        self.ui.puinode = self
        super().update(prev)

    def _tchanged(self, value): # editing
        if self.changing:
            self.changing = False
            return
        node = self.get_node()
        node.editing = True
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)

    def _tsubmitted(self, value): # finish editing
        node = self.get_node()
        node.editing = False
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._change(e)