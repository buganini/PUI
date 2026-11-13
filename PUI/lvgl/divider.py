from __future__ import annotations
from .base import *


class Divider(LBaseWidget):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
        lib.pui_lv_obj_set_height(self.ui, 1)
        lib.pui_lv_obj_set_width_pct(self.ui, 100)
        lib.pui_lv_obj_set_style_bg_color(self.ui, 0xCCCCCC)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)
