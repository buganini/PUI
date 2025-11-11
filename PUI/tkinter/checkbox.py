from .. import *
from .base import *

class Checkbox(TkBaseWidget):
    def __init__(self, text, model, value=None):
        super().__init__()
        self.text = text
        self.model = model
        self.value = text if value is None else value

    def update(self, prev):
        if prev and prev.ui:
            self.var = prev.var
            self.ui = prev.ui
        else:
            self.var = tk.IntVar()
            self.ui = tk.Checkbutton(self.tkparent.inner, text=self.text, variable=self.var, anchor="w")
        self.ui.configure(command=self._select)
        if checkbox_get(self.model, self.value):
            self.ui.select()
        else:
            self.ui.deselect()

        super().update(prev)

    def _select(self):
        node = self.get_node()
        checkbox_set(self.model, node.var.get() != 0, self.value)
