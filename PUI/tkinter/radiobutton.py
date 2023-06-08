from .. import *
from .base import *

class TkRadiobutton(TkBaseWidget):
    def __init__(self, text, value, model):
        super().__init__()
        self.text = text
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = tk.Radiobutton(self.tkparent.inner, text=self.text, anchor="w")
        if self.value  == self.model.value:
            self.ui.select()
        else:
            self.ui.deselect()
        self.ui.configure(command=self._select)
        super().update(prev)

    def _select(self):
        node = self.get_node()
        self.model.value = node.value
