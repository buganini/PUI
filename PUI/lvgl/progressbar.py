from __future__ import annotations
from .. import _typing as _t
from .base import *


class ProgressBar(LBaseWidget):
    def __init__(self, value: int = 0, minimum: int = 0, maximum: int = 100) -> None:
        super().__init__()
        self.value = value
        self.minimum = minimum
        self.maximum = maximum

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_bar_create(self.lv_parent_obj)
        lib.pui_lv_bar_set_range(self.ui, self.minimum, self.maximum)
        lib.pui_lv_bar_set_value(self.ui, self.value)
        super().update(prev)
