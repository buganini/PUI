from __future__ import annotations
from .. import _typing as _t
from ..common import Side
from ..selection import TabsMixin
from .base import *
from .base import _Native
from .layout import LBaseLayout, VBox


class Tabs(TabsMixin, LBaseWidget):
    """Tab header buttons above (or beside) a page area showing one Tab."""
    expand_x_prio = expand_y_prio = 3
    pui_terminal = False
    _default_size = ('content', 'content')

    def __init__(self, tabposition: Side = Side.Top, model: _t.Binding[_t.Any] | None = None) -> None:
        super().__init__(model=model)
        if not isinstance(tabposition, Side):
            raise TypeError('tabposition must be a Side')
        self.tabposition = tabposition

    @property
    def inner(self):
        return self._native.store.get('content') if self._native is not None else None

    def configure(self, prev):
        obj = self.ui
        store = self._native.store
        lib.lv_obj_set_style_bg_opa(obj, lib.LV_OPA_TRANSP, SEL)
        lib.lv_obj_set_style_border_width(obj, 0, SEL)
        lib.lv_obj_set_style_radius(obj, 0, SEL)
        lib.lv_obj_set_style_pad_all(obj, 0, SEL)
        lib.lv_obj_set_style_pad_row(obj, 0, SEL)
        lib.lv_obj_set_style_pad_column(obj, 0, SEL)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
        if 'content' not in store:
            header = store['header'] = lib.lv_obj_create(obj)
            lib.lv_obj_remove_flag(header, lib.LV_OBJ_FLAG_SCROLLABLE)
            lib.lv_obj_set_style_pad_all(header, 0, SEL)
            lib.lv_obj_set_style_pad_row(header, 0, SEL)
            lib.lv_obj_set_style_pad_column(header, 0, SEL)
            lib.lv_obj_set_style_radius(header, 0, SEL)
            lib.lv_obj_set_style_border_width(header, 0, SEL)
            content = store['content'] = lib.lv_obj_create(obj)
            lib.lv_obj_remove_flag(content, lib.LV_OBJ_FLAG_SCROLLABLE)
            lib.lv_obj_set_style_pad_all(content, 0, SEL)
            lib.lv_obj_set_style_radius(content, 0, SEL)
            lib.lv_obj_set_flex_flow(content, lib.LV_FLEX_FLOW_COLUMN)
            lib.lv_obj_set_flex_grow(content, 1)
            store['buttons'] = []
        for native in store['buttons']:
            native.node = self
        side = self.tabposition
        horizontal_header = side in (Side.Top, Side.Bottom)
        flows = {Side.Top: lib.LV_FLEX_FLOW_COLUMN, Side.Bottom: lib.LV_FLEX_FLOW_COLUMN_REVERSE,
                 Side.Left: lib.LV_FLEX_FLOW_ROW, Side.Right: lib.LV_FLEX_FLOW_ROW_REVERSE}
        lib.lv_obj_set_flex_flow(obj, flows[side])
        header, content = store['header'], store['content']
        lib.lv_obj_set_flex_flow(header, lib.LV_FLEX_FLOW_ROW if horizontal_header else lib.LV_FLEX_FLOW_COLUMN)
        if horizontal_header:
            lib.lv_obj_set_size(header, lib.lv_pct(100), lib.LV_SIZE_CONTENT)
        else:
            lib.lv_obj_set_size(header, lib.LV_SIZE_CONTENT, lib.lv_pct(100))
        lib.lv_obj_set_size(content, lib.lv_pct(100) if horizontal_header else lib.LV_SIZE_CONTENT,
                            lib.LV_SIZE_CONTENT if horizontal_header else lib.lv_pct(100))

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        super().addChild(idx, child)

    def _tabs(self):
        return [c for c in physical_children(self) if isinstance(c, Tab)]

    def postSync(self):
        if self.ui is not None:
            store = self._native.store
            tabs = self._tabs()
            buttons = store['buttons']
            while len(buttons) > len(tabs):
                native = buttons.pop()
                if native.obj is not None:
                    lib.lv_obj_delete(native.obj)
            while len(buttons) < len(tabs):
                button = lib.lv_button_create(store['header'])
                lib.lv_obj_set_style_radius(button, 0, SEL)
                label = lib.lv_label_create(button)
                lib.lv_obj_center(label)
                buttons.append(_Native(self, button, ()))
            for native, tab in zip(buttons, tabs):
                label = lib.lv_obj_get_child(native.obj, 0)
                lib.lv_label_set_text(label, text_bytes(tab.label))
        super().postSync()

    def _show_tab(self, index):
        store = self._native.store
        for i, (native, tab) in enumerate(zip(store['buttons'], self._tabs())):
            selected = i == index
            lib.lv_obj_set_state(native.obj, lib.LV_STATE_CHECKED, selected)
            if selected:
                lib.lv_obj_remove_flag(tab.outer, lib.LV_OBJ_FLAG_HIDDEN)
            else:
                lib.lv_obj_add_flag(tab.outer, lib.LV_OBJ_FLAG_HIDDEN)
            force_dim(tab, True)
            lib.lv_obj_set_flex_grow(tab.outer, 1)
            tab._relayout()

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_CLICKED:
            target = lib.lv_event_get_target_obj(e)
            buttons = [n.obj for n in self._native.store['buttons']]
            if target in buttons:
                self._native_selected(buttons.index(target))
                return
        super()._lv_event(code, e)


class Tab(VBox):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def _outer_padding(self):
        return 11


TabView = Tabs
TabPane = Tab
