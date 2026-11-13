from __future__ import annotations
from .. import _typing as _t
from .base import *


class Button(LBaseWidget):
    def __init__(self, text: _t.Any = '', *, icon: _t.Any = None, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.icon = icon
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self._label = prev._label
        else:
            self.ui = lib.pui_lv_btn_create(self.lv_parent_obj)
            self._label = None
        lib.pui_lv_obj_set_disabled(self.ui, 1 if self.disabled else 0)
        self._label = lib.pui_lv_btn_get_or_create_label(self.ui)
        lib.pui_lv_label_set_text(self._label, str(self.text).encode())
        super().update(prev)
