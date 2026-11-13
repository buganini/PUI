from __future__ import annotations
from .. import _typing as _t
from .base import *


class TextField(LBaseWidget):
    def __init__(self, text: _t.Any = '', *, placeholder: str = '') -> None:
        super().__init__()
        self.text = text
        self.placeholder = placeholder

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_textarea_create(self.lv_parent_obj)
            lib.pui_lv_textarea_set_one_line(self.ui, 1)
        lib.pui_lv_textarea_set_text(self.ui, str(self.text).encode())
        if self.placeholder:
            lib.pui_lv_textarea_set_placeholder(self.ui, self.placeholder.encode())
        super().update(prev)

    def _value_changed(self):
        text = lib.pui_lv_textarea_get_text(self.ui)
        if text != ffi.NULL:
            self._onChanged(ffi.string(text).decode())
