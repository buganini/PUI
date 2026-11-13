from __future__ import annotations
from .. import _typing as _t
from .base import *


class TextField(LBaseWidget):
    def __init__(self, model: _t.Binding[_t.Any] = None, edit_model: _t.Binding[_t.Any] | None = None, *, placeholder: str | None = None) -> None:
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_textarea_create(self.lv_parent_obj)
            lib.pui_lv_textarea_set_one_line(self.ui, 1)
        text = ''
        if self.model is not None and hasattr(self.model, 'value'):
            text = self.model.value if self.model.value is not None else ''
        lib.pui_lv_textarea_set_text(self.ui, str(text).encode())
        if self.placeholder:
            lib.pui_lv_textarea_set_placeholder(self.ui, self.placeholder.encode())
        super().update(prev)

    def _value_changed(self):
        text = lib.pui_lv_textarea_get_text(self.ui)
        if text != ffi.NULL:
            new_text = ffi.string(text).decode()
            if self.model is not None and hasattr(self.model, 'value'):
                self.model.value = new_text
                self.root.redraw()
