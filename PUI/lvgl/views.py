from __future__ import annotations
from .base import *
from .layout import LBaseLayout, VBox
from ..views import ViewsMixin


class Views(ViewsMixin, LBaseLayout):
    """Shows one child page at a time, selected by the model's key."""
    expand_x_prio = expand_y_prio = 3

    def _page(self):
        return VBox().layout(padding=0)

    def configure(self, prev):
        super().configure(prev)
        lib.lv_obj_set_flex_flow(self.ui, lib.LV_FLEX_FLOW_COLUMN)

    def _show_view(self, index):
        pages = list(physical_children(self))
        for i, page in enumerate(pages):
            if i == index:
                lib.lv_obj_remove_flag(page.outer, lib.LV_OBJ_FLAG_HIDDEN)
            else:
                lib.lv_obj_add_flag(page.outer, lib.LV_OBJ_FLAG_HIDDEN)
        configure_flex(self, False)
