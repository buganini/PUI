from __future__ import annotations
from .base import *


class Splitter(LBaseWidget):
    expand_x_prio = expand_y_prio = 3
    pui_terminal = False

    def __init__(self, vertical=False):
        super().__init__()
        self.vertical = vertical

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
        flow = lib.PUI_FLEX_FLOW_COLUMN if self.vertical else lib.PUI_FLEX_FLOW_ROW
        lib.pui_lv_obj_set_flex_flow(self.ui, flow)
        lib.pui_lv_obj_set_transparent(self.ui)
        lib.pui_lv_obj_set_style_pad_all(self.ui, 0)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_move_to_index(child.outer, idx)
            if self.vertical:
                if not child.layout_width:
                    lib.pui_lv_obj_set_width_pct(child.outer, 100)
            else:
                if not child.layout_height:
                    lib.pui_lv_obj_set_height_pct(child.outer, 100)

    def removeChild(self, idx, child):
        pass
