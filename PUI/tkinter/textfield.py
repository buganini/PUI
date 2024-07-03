from .. import *
from .base import *

class TextField(TkBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.variable = prev.variable
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if self.curr_value.set(model_value):
                self.variable.set(model_value)
        else:
            self.variable = tk.StringVar(self.tkparent.inner, model_value)
            self.variable.trace_add("write", self.on_variable_changed)
            self.curr_value = Prop(model_value)
            self.ui = tk.Entry(self.tkparent.inner, textvariable=self.variable)
        super().update(prev)

    def on_variable_changed(self, var, index, mode):
        value = self.variable.get()
        self.model.value = value
