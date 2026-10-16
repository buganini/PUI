from .. import *
from .base import *

class Checkbox(TkBaseWidget):
    ttk_style = "TCheckbutton"
    def __init__(self, text, model, value=None, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled
        self.model = model
        self.value = text if value is None else value

    def update(self, prev):
        if prev and prev.ui:
            self.var = prev.var
            self.ui = prev.ui
        else:
            self.var = tk.IntVar(self.tkparent.inner)
            self.ui = ttk.Checkbutton(self.tkparent.inner, text=self.text, variable=self.var)
        self.ui.configure(text=self.text, command=self._select)
        self.var.set(int(checkbox_get(self.model, self.value)))

        self.ui.configure(state='normal' if self.enabled else 'disabled')
        super().update(prev)

    def _select(self):
        node = self.get_node()
        checkbox_set(node.model, node.var.get() != 0, node.value)
        node._clicked()
