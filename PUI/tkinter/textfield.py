from .. import *
from .base import *

class TextField(TkBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def update(self, prev):
        value = self.model.value
        if prev and prev.ui:
            self.variable = prev.variable
            self.ui = prev.ui
            if prev.last_value != value:
                self.variable.set(value)
            self.last_value = value
        else:
            self.variable = tk.StringVar(self.tkparent.inner, str(value))
            self.variable.trace_add("write", self.on_variable_changed)
            self.last_value = value
            self.ui = tk.Entry(self.tkparent.inner, textvariable=self.variable)
        super().update(prev)

    def on_variable_changed(self, var, index, mode):
        value = self.variable.get()
        self.model.value = value
