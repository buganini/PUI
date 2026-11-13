"""Menu bar with drop-down popups on LVGL's top layer.

MenuBar is a row at the top of its Window. Menu and MenuAction are
declarations: the bar renders buttons for them and opens popup lists
(submenus open to the right). Clicking outside closes the popups.
"""
from __future__ import annotations
from .base import *
from .layout import Spacer
from .overlay import Handlers

_SYMBOL_RIGHT = b'\xef\x81\x94'


class MenuAction(PUINode):
    pui_terminal = True

    def __init__(self, text, *, native=True):
        super().__init__()
        self.text = text
        self.native = native
        self.onTriggered = None

    def trigger(self, callback, *cb_args, **cb_kwargs):
        self.onTriggered = (callback, cb_args, cb_kwargs)
        return self

    def _triggered(self):
        node = self.get_node()
        if not node.destroyed and node.onTriggered:
            callback, args, kwargs = node.onTriggered
            callback(*args, **kwargs)


class Menu(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text


def _items(node):
    for child in node.children:
        child = child.get_node()
        if child.pui_virtual:
            yield from _items(child)
        else:
            yield child


class _Popups:
    """The open popup chain; at most one menu bar has popups at a time."""

    def __init__(self):
        self.catcher = None
        self.levels = []          # popup objects, one per depth
        self.handlers = Handlers()

    def close(self, depth=0):
        while len(self.levels) > depth:
            popup = self.levels.pop()
            lib.lv_obj_delete(popup)
        if depth == 0:
            self.handlers.clear()
            if self.catcher is not None:
                lib.lv_obj_delete(self.catcher)
                self.catcher = None

    def open(self, menu, anchor, depth):
        self.close(depth)
        if self.catcher is None:
            catcher = self.catcher = lib.lv_obj_create(lib.lv_layer_top())
            lib.lv_obj_remove_style_all(catcher)
            lib.lv_obj_set_size(catcher, lib.lv_pct(100), lib.lv_pct(100))
            lib.lv_obj_add_flag(catcher, lib.LV_OBJ_FLAG_CLICKABLE)
            self.handlers.on(catcher, lib.LV_EVENT_CLICKED, lambda c, e: runtime.post(self.close))
        popup = lib.lv_obj_create(self.catcher)
        lib.lv_obj_set_size(popup, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
        lib.lv_obj_set_style_min_width(popup, 140, SEL)
        lib.lv_obj_set_flex_flow(popup, lib.LV_FLEX_FLOW_COLUMN)
        lib.lv_obj_set_style_pad_all(popup, 4, SEL)
        lib.lv_obj_set_style_pad_row(popup, 0, SEL)
        lib.lv_obj_set_style_radius(popup, 4, SEL)
        lib.lv_obj_remove_flag(popup, lib.LV_OBJ_FLAG_SCROLLABLE)
        self.levels.append(popup)
        for item in _items(menu):
            if not isinstance(item, (Menu, MenuAction)):
                continue
            row = lib.lv_obj_create(popup)
            lib.lv_obj_remove_style_all(row)
            lib.lv_obj_set_size(row, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
            lib.lv_obj_set_style_min_width(row, lib.lv_pct(100), SEL)
            lib.lv_obj_set_flex_flow(row, lib.LV_FLEX_FLOW_ROW)
            lib.lv_obj_set_style_pad_all(row, 6, SEL)
            lib.lv_obj_set_style_pad_column(row, 12, SEL)
            lib.lv_obj_set_style_bg_color(row, lib.lv_color_hex(0x2196F3), lib.LV_STATE_PRESSED)
            lib.lv_obj_set_style_bg_opa(row, lib.LV_OPA_COVER, lib.LV_STATE_PRESSED)
            lib.lv_obj_add_flag(row, lib.LV_OBJ_FLAG_CLICKABLE)
            label = lib.lv_label_create(row)
            lib.lv_label_set_text(label, text_bytes(item.text))
            lib.lv_obj_set_flex_grow(label, 1)
            if isinstance(item, Menu):
                lib.lv_label_set_text(lib.lv_label_create(row), _SYMBOL_RIGHT)
                self.handlers.on(row, lib.LV_EVENT_CLICKED,
                                 lambda c, e, item=item, row=row, depth=depth: runtime.post(
                                     lambda: self.open(item.get_node(), row, depth + 1)))
            else:
                self.handlers.on(row, lib.LV_EVENT_CLICKED,
                                 lambda c, e, item=item: runtime.post(lambda: self._run(item)))
        lib.lv_obj_update_layout(popup)
        lib.lv_obj_align_to(popup, anchor,
                            lib.LV_ALIGN_OUT_BOTTOM_LEFT if depth == 0 else lib.LV_ALIGN_OUT_RIGHT_TOP, 0, 0)

    def _run(self, item):
        self.close()
        item._triggered()


_popups = _Popups()


class MenuBar(LBaseWidget):
    pui_terminal = False
    pui_outoforder = True
    _default_size = (('pct', 100), 'content')

    def __init__(self, *, native=True):
        super().__init__()
        self.native = native

    def configure(self, prev):
        obj = self.ui
        lib.lv_obj_set_flex_flow(obj, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(obj, lib.LV_FLEX_ALIGN_START, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        lib.lv_obj_set_style_pad_all(obj, 2, SEL)
        lib.lv_obj_set_style_pad_column(obj, 2, SEL)
        lib.lv_obj_set_style_radius(obj, 0, SEL)
        lib.lv_obj_set_style_border_width(obj, 0, SEL)
        lib.lv_obj_set_style_bg_color(obj, lib.lv_color_hex(0xEEEEEE), SEL)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
        store = self._native.store
        if 'buttons' not in store:
            store['buttons'] = []
            store['handlers'] = Handlers()
            store['on_delete'] = [store['handlers'].clear]

    def addChild(self, idx, child):
        if not isinstance(child, (Menu, MenuAction, Spacer)):
            raise TypeError('MenuBar children must be Menu, MenuAction or Spacer')
        super().addChild(idx, child)

    def postSync(self):
        if self.ui is None:
            return super().postSync()
        store = self._native.store
        buttons = store['buttons']
        entries = [c for c in _items(self) if isinstance(c, (Menu, MenuAction, Spacer))]
        menus = [c for c in entries if not isinstance(c, Spacer)]
        while len(buttons) > len(menus):
            lib.lv_obj_delete(buttons.pop())
        while len(buttons) < len(menus):
            i = len(buttons)
            button = lib.lv_button_create(self.ui)
            lib.lv_obj_set_style_bg_opa(button, lib.LV_OPA_TRANSP, SEL)
            lib.lv_obj_set_style_shadow_width(button, 0, SEL)
            lib.lv_obj_set_style_text_color(button, lib.lv_color_hex(0x202020), SEL)
            lib.lv_obj_set_style_pad_top(button, 4, SEL)
            lib.lv_obj_set_style_pad_bottom(button, 4, SEL)
            lib.lv_obj_set_style_bg_opa(button, lib.LV_OPA_COVER, lib.LV_STATE_PRESSED)
            lib.lv_label_create(button)
            store['handlers'].on(button, lib.LV_EVENT_CLICKED,
                                 lambda c, e, i=i: runtime.post(lambda: self.get_node()._pressed(i)))
            buttons.append(button)
        index = 0
        for position, entry in enumerate(entries):
            if isinstance(entry, Spacer):
                lib.lv_obj_move_to_index(entry.outer, position)
                lib.lv_obj_set_flex_grow(entry.outer, 1)
                continue
            button = buttons[index]
            lib.lv_label_set_text(lib.lv_obj_get_child(button, 0), text_bytes(entry.text))
            lib.lv_obj_move_to_index(button, position)
            index += 1
        store['menus'] = menus
        super().postSync()

    def _pressed(self, index):
        if self.destroyed or self.ui is None:
            return
        store = self._native.store
        menus = store.get('menus', [])
        if index >= len(menus):
            return
        item = menus[index].get_node()
        if isinstance(item, MenuAction):
            _popups.close()
            item._triggered()
        else:
            _popups.open(item, store['buttons'][index], 0)

    def destroy(self, direct):
        _popups.close()
        super().destroy(direct)
