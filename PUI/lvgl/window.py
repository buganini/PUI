from __future__ import annotations
from .. import _typing as _t
from .base import *


class Window(LBaseWidget):
    pui_terminal = False

    def __init__(self, *, title: str = '', size: tuple[int, int] | None = None) -> None:
        super().__init__()
        self.title = title

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lvgl_screen_active()
        super().update(prev)

    def destroy(self, direct):
        if direct and self.ui:
            lib.pui_lv_obj_clean(self.ui)
        self.ui = None
        PUINode.destroy(self, direct)

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_move_to_index(child.outer, idx)
            if not child.layout_width:
                lib.pui_lv_obj_set_width_pct(child.outer, 100)
            if not child.layout_height:
                lib.pui_lv_obj_set_height_pct(child.outer, 100)

    def removeChild(self, idx, child):
        pass
