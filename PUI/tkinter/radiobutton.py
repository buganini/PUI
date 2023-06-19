from .. import *
from .base import *

class RadioButton(TkBaseWidget):
    def __init__(self, text, value, model):
        super().__init__()
        self.var = None
        self.text = text
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.var = prev.var
            self.ui = prev.ui
        else:
            self.var = tk.StringVar()
            self.ui = tk.Radiobutton(self.tkparent.inner, text=self.text, variable=self.var, value=self.value, anchor="w")

        self.var.set(self.model.value)
        self.ui.configure(command=self._select)
        super().update(prev)

    def _select(self):
        node = self.get_node()
        self.model.value = node.value
