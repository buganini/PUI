from __future__ import annotations
from .. import _typing as _t
from .base import *


class Checkbox(LBaseWidget):
    def __init__(self, text: _t.Any = '', model: _t.Binding[_t.Any] = None, value: _t.Any = None, *, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.model = model
        self.value = text if value is None else value
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_checkbox_create(self.lv_parent_obj)
        lib.pui_lv_checkbox_set_text(self.ui, str(self.text).encode())
        checked = False
        if self.model is not None and hasattr(self.model, 'value'):
            checked = self.model.value == self.value if self.value is not None else bool(self.model.value)
        lib.pui_lv_checkbox_set_checked(self.ui, 1 if checked else 0)
        lib.pui_lv_obj_set_disabled(self.ui, 1 if self.disabled else 0)
        super().update(prev)

    def _value_changed(self):
        checked = lib.pui_lv_checkbox_is_checked(self.ui)
        if self.model is not None and hasattr(self.model, 'value'):
            if self.value is not None:
                self.model.value = self.value if checked else None
            else:
                self.model.value = bool(checked)
            self.root.redraw()
