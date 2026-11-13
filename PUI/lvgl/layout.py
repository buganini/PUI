from ..grid import GridMixin
from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *
from .label import Label
from .text import Text


class LBaseLayout(LBaseWidget):
    """Transparent, non-scrolling container; top-level layouts get 11px padding."""
    pui_terminal = False
    pui_reflow_children = True
    _default_size = ('content', 'content')

    def _outer_padding(self):
        parent = self.non_virtual_parent
        return 0 if isinstance(parent, LBaseLayout) else 11

    def configure(self, prev):
        obj = self.ui
        lib.lv_obj_set_style_bg_opa(obj, lib.LV_OPA_TRANSP, SEL)
        lib.lv_obj_set_style_border_width(obj, 0, SEL)
        lib.lv_obj_set_style_radius(obj, 0, SEL)
        lib.lv_obj_set_style_pad_all(obj, self._outer_padding(), SEL)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)

    def _fills(self):
        return fills_axis(self.ui, True), fills_axis(self.ui, False)

    def _relayout(self):
        if self.ui is not None and self._native.store.get('fills') != self._fills():
            self.postSync()


class _Box(_BoxMixin, LBaseLayout):
    container_x = False
    container_y = False

    def configure(self, prev):
        super().configure(prev)
        obj = self.ui
        horizontal = self.container_x
        if horizontal:
            flow = lib.LV_FLEX_FLOW_ROW_REVERSE if self._native_box_inverse and self._inverse else lib.LV_FLEX_FLOW_ROW
        else:
            flow = lib.LV_FLEX_FLOW_COLUMN_REVERSE if self._native_box_inverse and self._inverse else lib.LV_FLEX_FLOW_COLUMN
        lib.lv_obj_set_flex_flow(obj, flow)
        lib.lv_obj_set_flex_align(obj, lib.LV_FLEX_ALIGN_START,
                                  lib.LV_FLEX_ALIGN_CENTER if horizontal else lib.LV_FLEX_ALIGN_START,
                                  lib.LV_FLEX_ALIGN_START)
        gap = round(self.gap)
        lib.lv_obj_set_style_pad_row(obj, gap, SEL)
        lib.lv_obj_set_style_pad_column(obj, gap, SEL)

    def postSync(self):
        if self.ui is not None:
            self._native.store['fills'] = self._fills()
            configure_flex(self, self.container_x)
        super().postSync()


class HBox(_Box):
    container_x = True
    expand_x_prio = 3
    expand_y_prio = 1


class VBox(_Box):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 3


class _AdaptiveLayout(_Box):
    pass


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass


class Spacer(LBaseWidget):
    pui_movable = False

    def __init__(self):
        super().__init__()
        self.layout_weight = 1

    def create(self, parent):
        obj = lib.lv_obj_create(parent)
        lib.lv_obj_remove_style_all(obj)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_CLICK_FOCUSABLE)
        return obj

    _default_size = (0, 0)


class Stack(LBaseLayout):
    """All children share one grid cell; later children are drawn on top."""
    expand_x_prio = 3
    expand_y_prio = 3
    pui_reversed_order = False

    def configure(self, prev):
        super().configure(prev)
        lib.lv_obj_set_style_pad_row(self.ui, 0, SEL)
        lib.lv_obj_set_style_pad_column(self.ui, 0, SEL)

    def postSync(self):
        if self.ui is not None:
            fx, fy = self._native.store['fills'] = self._fills()
            tracks = ffi.new('int32_t[4]', [grid_fr(1) if fx else lib.LV_GRID_CONTENT, lib.LV_GRID_TEMPLATE_LAST,
                                            grid_fr(1) if fy else lib.LV_GRID_CONTENT, lib.LV_GRID_TEMPLATE_LAST])
            self._native.store['tracks'] = tracks
            lib.lv_obj_set_grid_dsc_array(self.ui, tracks, tracks + 2)
            for child in physical_children(self):
                if isinstance(child, Spacer):
                    lib.lv_obj_add_flag(child.outer, lib.LV_OBJ_FLAG_IGNORE_LAYOUT)
                    continue
                lib.lv_obj_set_grid_cell(child.outer,
                                         lib.LV_GRID_ALIGN_STRETCH if fx else lib.LV_GRID_ALIGN_START, 0, 1,
                                         lib.LV_GRID_ALIGN_STRETCH if fy else lib.LV_GRID_ALIGN_START, 0, 1)
                hook = getattr(child, '_relayout', None)
                if hook is not None:
                    hook()
        super().postSync()


class Grid(GridMixin, LBaseLayout):
    expand_x_prio = 1
    expand_y_prio = 1
    pui_grid_layout = True

    def adopt(self, prev):
        self.mounted = prev.mounted

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)
        super().addChild(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        super().removeChild(idx, child)

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_SIZE_CHANGED and self._native.store.get('fills') is not None:
            store = self._native.store
            if not store.get('remeasure'):
                store['remeasure'] = True

                def remeasure():
                    store['remeasure'] = False
                    node = self.get_node()
                    if node.ui is not None and not node.destroyed:
                        node._configure_tracks()
                runtime.post(remeasure)
        super()._lv_event(code, e)

    def configure(self, prev):
        if prev is None or prev.ui is None:
            self.mounted = []
            self._native.listen(lib.LV_EVENT_SIZE_CHANGED)
        LBaseLayout.configure(self, prev)
        row_gap, column_gap = self.gap
        lib.lv_obj_set_style_pad_row(self.ui, round(row_gap), SEL)
        lib.lv_obj_set_style_pad_column(self.ui, round(column_gap), SEL)

    @staticmethod
    def _natural(child, horizontal):
        """Requested size, independent of a stretched allocation."""
        o = child.outer
        calc = lib.lv_obj_calc_dynamic_width if horizontal else lib.lv_obj_calc_dynamic_height
        requested = lib.lv_obj_get_style_width(o, SEL) if horizontal else lib.lv_obj_get_style_height(o, SEL)
        size = calc(o, lib.LV_STYLE_WIDTH if horizontal else lib.LV_STYLE_HEIGHT)
        if requested == lib.LV_SIZE_CONTENT and isinstance(child, (Label, Text)):
            point = ffi.new('lv_point_t *')
            limit = (lib.LV_COORD_MAX if lib.lv_obj_get_style_width(o, SEL) == lib.LV_SIZE_CONTENT
                     else lib.lv_obj_get_content_width(o))
            lib.lv_text_get_size(point, lib.lv_label_get_text(o), lib.lv_obj_get_style_text_font(o, SEL),
                                 lib.lv_obj_get_style_text_letter_space(o, SEL),
                                 lib.lv_obj_get_style_text_line_space(o, SEL), limit, 0)
            size = (point.x + lib.lv_obj_get_style_space_left(o, SEL) + lib.lv_obj_get_style_space_right(o, SEL)
                    if horizontal else
                    point.y + lib.lv_obj_get_style_space_top(o, SEL) + lib.lv_obj_get_style_space_bottom(o, SEL))
        minimum = calc(o, lib.LV_STYLE_MIN_WIDTH if horizontal else lib.LV_STYLE_MIN_HEIGHT)
        maximum = calc(o, lib.LV_STYLE_MAX_WIDTH if horizontal else lib.LV_STYLE_MAX_HEIGHT)
        size = max(minimum, min(size, maximum))
        if horizontal:
            size += lib.lv_obj_get_style_margin_left(o, SEL) + lib.lv_obj_get_style_margin_right(o, SEL)
        else:
            size += lib.lv_obj_get_style_margin_top(o, SEL) + lib.lv_obj_get_style_margin_bottom(o, SEL)
        return size

    def _measure(self, cells, weights, horizontal, fill):
        count = len(weights)
        gap = round(self.gap[1] if horizontal else self.gap[0])
        sizes = [0] * count
        items = []
        for child, (row, column, rowspan, columnspan) in cells:
            if not child._visible:
                continue
            start, span = (column, columnspan) if horizontal else (row, rowspan)
            items.append((span, start, self._natural(child, horizontal)))
        # Single cells first; a span shares its unmet extent across its tracks.
        for span, start, size in sorted(items, key=lambda item: item[0]):
            tracks = range(start, start + span)
            extra = max(0, size - (gap * (span - 1) + sum(sizes[i] for i in tracks)))
            total = sum(weights[i] for i in tracks)
            shares = [weights[i] for i in tracks] if total else [1] * span
            total = total or span
            for i, share in zip(tracks, shares):
                if share:
                    part = extra * share // total
                    sizes[i] += part
                    extra -= part
                    total -= share
        if fill:
            content = lib.lv_obj_get_content_width(self.ui) if horizontal else lib.lv_obj_get_content_height(self.ui)
            available = max(0, content - gap * (count - 1) - sum(sizes))
            total = sum(weights)
            for i, weight in enumerate(weights):
                if weight and total:
                    part = (available * weight + total // 2) // total
                    sizes[i] += part
                    available -= part
                    total -= weight
        return sizes

    def _configure_tracks(self):
        cells = self._native.store.get('cells') or []
        fx, fy = self._native.store['fills'] = self._fills()
        col_weights, row_weights = self.grid_stretches(cells)
        ncols = max((col + span for _, (_, col, _, span) in cells), default=0)
        nrows = max((row + span for _, (row, _, span, _) in cells), default=0)
        col_weights = list(col_weights) + [0] * (ncols - len(col_weights))
        row_weights = list(row_weights) + [0] * (nrows - len(row_weights))
        lib.lv_obj_update_layout(self.ui)
        columns = self._measure(cells, col_weights, True, fx)
        rows = self._measure(cells, row_weights, False, fy)
        values = columns + [lib.LV_GRID_TEMPLATE_LAST] + rows + [lib.LV_GRID_TEMPLATE_LAST]
        if self._native.store.get('track_values') == values:
            return
        array = ffi.new('int32_t[]', values)
        self._native.store['tracks'] = array  # LVGL borrows the descriptor arrays
        self._native.store['track_values'] = values
        lib.lv_obj_set_grid_dsc_array(self.ui, array, array + ncols + 1)

    def postSync(self):
        if self.ui is None:
            return super().postSync()
        self.mounted[:] = [child.get_node() for child in self.mounted]
        cells = self.grid_cells([c for c in self.mounted if isinstance(c, LBaseWidget) and c.ui is not None])
        self._native.store['cells'] = cells
        for child, (row, column, rowspan, columnspan) in cells:
            # Like Qt's grid, controls fill their cell unless sized explicitly.
            lib.lv_obj_set_grid_cell(child.outer,
                                     lib.LV_GRID_ALIGN_START if child.layout_width is not None else lib.LV_GRID_ALIGN_STRETCH,
                                     column, columnspan,
                                     lib.LV_GRID_ALIGN_CENTER if child.layout_height is not None else lib.LV_GRID_ALIGN_STRETCH,
                                     row, rowspan)
            release_dim(child, True)
            release_dim(child, False)
        self._configure_tracks()
        for child, _ in cells:
            hook = getattr(child, '_relayout', None)
            if hook is not None:
                hook()
        LBaseWidget.postSync(self)
