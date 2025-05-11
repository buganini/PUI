from .. import *
from .base import *

class TextField(TkBaseWidget):
    def __init__(self, model, edit_model=None):
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.editing = False

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.variable = prev.variable
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if self.curr_value.set(model_value) and not self.editing:
                self.variable.set(model_value)
        else:
            self.variable = tk.StringVar(self.tkparent.inner, model_value)
            self.variable.trace_add("write", self.on_variable_changed)
            self.curr_value = Prop(model_value)
            self.ui = tk.Entry(self.tkparent.inner, textvariable=self.variable)
            self.ui.bind('<Return>', self.on_return)
            self.ui.bind('<FocusOut>', self.on_focus_out)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_variable_changed(self, var, index, mode): # editing
        node = self.get_node()
        node.editing = True
        if node.edit_model:
            node.edit_model.value = self.variable.get()
        self._input()

    def on_change(self): # finish editing
        node = self.get_node()
        node.editing = False
        value = self.variable.get()
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        self._change()

    def on_return(self, e):
        self.on_change()

    def on_focus_out(self, e):
        self.on_change()
