from .. import *
from .base import *

class RadioButton(TkBaseWidget):
    ttk_style = "TRadiobutton"
    def __init__(self, text, value, model, *, enabled=True):
        super().__init__()
        self.var = None
        self.text = text
        self.enabled = enabled
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.var = prev.var
            self.ui = prev.ui
        else:
            self.var = tk.StringVar(self.tkparent.inner)
            self.ui = ttk.Radiobutton(self.tkparent.inner, text=self.text, variable=self.var, value=self.value)

        self.var.set(self.model.value)
        self.ui.configure(text=self.text, value=self.value, command=self._select)
        self.ui.configure(state='normal' if self.enabled else 'disabled')
        super().update(prev)

    def _select(self):
        node = self.get_node()
        node.model.value = node.value
        node._clicked()
