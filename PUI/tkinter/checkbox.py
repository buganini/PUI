from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Checkbox(TkBaseWidget):
    ttk_style = "TCheckbutton"
    def __init__(
        self,
        text: _t.Any,
        model: _t.Binding[_t.Any],
        value: _t.Any = None,
        *,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self.text = text
        self.disabled = disabled
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

        self.ui.configure(state='disabled' if self.disabled else 'normal')
        super().update(prev)

    def _select(self):
        node = self.get_node()
        checkbox_set(node.model, node.var.get() != 0, node.value)
        node._clicked()
