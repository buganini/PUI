from __future__ import annotations
from .base import *


class Divider(LBaseWidget):
    """A 1px line across the parent's cross axis."""
    pui_movable = False

    def create(self, parent):
        obj = lib.lv_obj_create(parent)
        lib.lv_obj_remove_style_all(obj)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
        lib.lv_obj_set_style_bg_color(obj, lib.lv_color_hex(0x808080), SEL)
        lib.lv_obj_set_style_bg_opa(obj, lib.LV_OPA_COVER, SEL)
        return obj

    def _column_parent(self):
        parent = self.pui_dom_parent.get_node() if self.pui_dom_parent is not None else None
        return not getattr(parent, 'container_x', False)

    def update(self, prev):
        column = self._column_parent()
        self.expand_x_prio = 1 if column else 0
        self.expand_y_prio = 0 if column else 1
        self._default_size = (('pct', 100), 1) if column else (1, ('pct', 100))
        super().update(prev)
