from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Checkbox(TBase):
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
            self.ui = prev.ui
            self.ui.value = checkbox_get(self.model, self.value)
        else:
            self.ui = widgets.Checkbox(self.text, checkbox_get(self.model, self.value))

        self.ui.puinode = self
        self.ui.disabled = self.disabled
        super().update(prev)

    def _changed(self, value):
        checkbox_set(self.model, value, self.value)
