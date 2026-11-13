from __future__ import annotations
from .base import *


class Views(LBaseWidget):
    """Tab-like view container — shows one child at a time based on index."""
    pui_terminal = False

    def __init__(self, index: int = 0) -> None:
        super().__init__()
        self.index = index

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
        lib.pui_lv_obj_set_transparent(self.ui)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_set_hidden(child.ui, 0 if idx == self.index else 1)

    def removeChild(self, idx, child):
        pass
