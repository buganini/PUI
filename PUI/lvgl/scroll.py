from __future__ import annotations
from .. import _typing as _t
from .base import *


class Scroll(LBaseWidget):
    pui_terminal = False
    END = -0.0

    def __init__(self, vertical: bool | None = None, horizontal: bool | None = False) -> None:
        super().__init__()

    def scrollX(self, pos=0):
        return self

    def scrollY(self, pos=0):
        return self

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_scroll_create(self.lv_parent_obj)
        lib.pui_lv_obj_set_flex_flow(self.ui, lib.PUI_FLEX_FLOW_COLUMN)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_move_to_index(child.outer, idx)

    def removeChild(self, idx, child):
        pass
