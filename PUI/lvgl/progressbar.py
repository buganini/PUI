from __future__ import annotations
from .. import _typing as _t
from .base import *


class ProgressBar(LBaseWidget):
    def __init__(self, progress: _t.Number = 0, maximum: _t.Number = 1) -> None:
        super().__init__()
        self.progress = progress * 100
        self.maximum = maximum * 100

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_bar_create(self.lv_parent_obj)
        lib.pui_lv_bar_set_range(self.ui, 0, int(self.maximum))
        lib.pui_lv_bar_set_value(self.ui, int(self.progress))
        super().update(prev)
