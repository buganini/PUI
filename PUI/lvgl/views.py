from __future__ import annotations
from .base import *
from .layout import VBox
from ..views import ViewsMixin


class Views(ViewsMixin, LBaseWidget):
    """Tab-like view container — shows one child at a time based on selection key."""
    expand_x_prio = expand_y_prio = 3

    def _page(self):
        return VBox().layout(padding=0)

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
            lib.pui_lv_obj_move_to_index(child.outer, idx)

    def removeChild(self, idx, child):
        pass

    def _show_view(self, index):
        for i, child in enumerate(self.children):
            if isinstance(child, LBaseWidget) and child.ui is not None:
                lib.pui_lv_obj_set_hidden(child.ui, 0 if i == index else 1)
