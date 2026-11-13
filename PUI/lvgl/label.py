from __future__ import annotations
from .. import _typing as _t
from .base import *


class Label(LBaseWidget):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_label_create(self.lv_parent_obj)
            lib.pui_lv_obj_set_clickable(self.ui, 1)
        lib.pui_lv_label_set_text(self.ui, str(self.text).encode())
        super().update(prev)
