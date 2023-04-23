from .. import *
from .base import *

class TkEntry(TkBaseWidget):
    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    def update(self, prev):
        value = self.model.value
        if prev and hasattr(prev, "ui"):
            self.variable = prev.variable
            self.ui = prev.ui
            if prev.last_value != value:
                self.variable.set(value)
            self.last_value = value
        else:
            self.variable = tk.StringVar(self.parent.ui, str(value))
            self.variable.trace_add("write", self.on_variable_changed)
            self.last_value = value
            self.ui = tk.Entry(self.parent.ui, textvariable=self.variable, **self.kwargs)

    def on_variable_changed(self, var, index, mode):
        value = self.variable.get()
        self.model.value = value
