from ..grid import GridMixin, native_stretches
from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *


def _priority(child, axis):
    from ..expansion import priority
    return priority(child, axis)


class HBox(_BoxMixin, LBaseWidget):
    container_x = True
    expand_x_prio = 3
    expand_y_prio = 1
    pui_terminal = False

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
        lib.pui_lv_obj_set_flex_flow(self.ui, lib.PUI_FLEX_FLOW_ROW)
        lib.pui_lv_obj_set_flex_align(self.ui,
            lib.PUI_FLEX_ALIGN_START, lib.PUI_FLEX_ALIGN_CENTER, lib.PUI_FLEX_ALIGN_START)
        lib.pui_lv_obj_set_transparent(self.ui)
        lib.pui_lv_obj_set_style_pad_all(self.ui, 0)
        lib.pui_lv_obj_set_style_pad_column(self.ui, round(self.gap))
        lib.pui_lv_obj_set_size_content(self.ui)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_move_to_index(child.outer, idx)

    def removeChild(self, idx, child):
        pass

    def postSync(self):
        super().postSync()


class VBox(_BoxMixin, LBaseWidget):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 3
    pui_terminal = False

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
        lib.pui_lv_obj_set_flex_flow(self.ui, lib.PUI_FLEX_FLOW_COLUMN)
        lib.pui_lv_obj_set_flex_align(self.ui,
            lib.PUI_FLEX_ALIGN_START, lib.PUI_FLEX_ALIGN_START, lib.PUI_FLEX_ALIGN_START)
        lib.pui_lv_obj_set_transparent(self.ui)
        lib.pui_lv_obj_set_style_pad_all(self.ui, 0)
        lib.pui_lv_obj_set_style_pad_row(self.ui, round(self.gap))
        lib.pui_lv_obj_set_size_content(self.ui)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_move_to_index(child.outer, idx)

    def removeChild(self, idx, child):
        pass

    def postSync(self):
        super().postSync()


class Spacer(LBaseWidget):
    def __init__(self):
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
        lib.pui_lv_obj_set_transparent(self.ui)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)


class Grid(GridMixin, LBaseWidget):
    expand_x_prio = 1
    expand_y_prio = 1
    pui_terminal = False
    pui_grid_layout = True

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui = prev.ui
            self.mounted = prev.mounted
        else:
            self.ui = lib.pui_lv_obj_create(self.lv_parent_obj)
            self.mounted = []
        lib.pui_lv_obj_set_transparent(self.ui)
        lib.pui_lv_obj_set_scrollable(self.ui, 0)
        super().update(prev)

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        if isinstance(child, LBaseWidget) and child.ui:
            lib.pui_lv_obj_delete(child.ui)

    def postSync(self):
        cells = self.grid_cells(self.mounted)
        if not cells:
            return
        max_col = max(col + colspan for _, (_, col, _, colspan) in cells)
        max_row = max(row + rowspan for _, (row, _, rowspan, _) in cells)
        lib.pui_lv_obj_set_grid(self.ui, max_col, max_row)
        for child, (row, column, rowspan, columnspan) in cells:
            if not child._visible:
                lib.pui_lv_obj_set_hidden(child.outer, 1)
                continue
            lib.pui_lv_obj_set_hidden(child.outer, 0)
            lib.pui_lv_obj_set_grid_cell(child.outer, column, row, columnspan, rowspan)
        super().postSync()


class _AdaptiveLayout(HBox):
    pass


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass


class Stack(LBaseWidget):
    expand_x_prio = 3
    expand_y_prio = 3
    pui_terminal = False

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
