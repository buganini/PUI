from __future__ import annotations
from .. import _typing as _t
from .base import *


class Checkbox(LBaseWidget):
    def __init__(self, text: _t.Any = '', value: _t.Any = False) -> None:
        super().__init__()
        self.text = text
        self.value = value

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_checkbox_create(self.lv_parent_obj)
        lib.pui_lv_checkbox_set_text(self.ui, str(self.text).encode())
        lib.pui_lv_checkbox_set_checked(self.ui, 1 if self.value else 0)
        super().update(prev)

    def _value_changed(self):
        checked = lib.pui_lv_checkbox_is_checked(self.ui)
        self._clicked(checked=bool(checked))
