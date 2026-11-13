"""Dialog panels on LVGL's top layer, shared by Modal and table/tree editors."""
from __future__ import annotations
from .base import *


def create_dialog(title=None, width=None, height=None, on_close=None):
    """Return (backdrop, panel, body): a dimmed full-screen backdrop with a
    centered panel, an optional title bar with a close button, and a body
    column for content. Deleting the backdrop removes everything."""
    backdrop = lib.lv_obj_create(lib.lv_layer_top())
    lib.lv_obj_remove_style_all(backdrop)
    lib.lv_obj_set_size(backdrop, lib.lv_pct(100), lib.lv_pct(100))
    lib.lv_obj_set_style_bg_color(backdrop, lib.lv_color_hex(0x000000), SEL)
    lib.lv_obj_set_style_bg_opa(backdrop, 96, SEL)
    lib.lv_obj_add_flag(backdrop, lib.LV_OBJ_FLAG_CLICKABLE)  # block input below
    lib.lv_obj_remove_flag(backdrop, lib.LV_OBJ_FLAG_SCROLLABLE)

    panel = lib.lv_obj_create(backdrop)
    lib.lv_obj_set_flex_flow(panel, lib.LV_FLEX_FLOW_COLUMN)
    lib.lv_obj_set_style_pad_all(panel, 0, SEL)
    lib.lv_obj_set_style_pad_row(panel, 0, SEL)
    lib.lv_obj_remove_flag(panel, lib.LV_OBJ_FLAG_SCROLLABLE)
    lib.lv_obj_set_width(panel, int(width) if width else lib.LV_SIZE_CONTENT)
    lib.lv_obj_set_height(panel, int(height) if height else lib.LV_SIZE_CONTENT)
    lib.lv_obj_set_style_min_width(panel, 240, SEL)
    lib.lv_obj_set_style_max_width(panel, lib.lv_pct(95), SEL)
    lib.lv_obj_set_style_max_height(panel, lib.lv_pct(95), SEL)
    lib.lv_obj_align(panel, lib.LV_ALIGN_CENTER, 0, 0)

    close = None
    if title is not None or on_close is not None:
        bar = lib.lv_obj_create(panel)
        lib.lv_obj_remove_flag(bar, lib.LV_OBJ_FLAG_SCROLLABLE)
        lib.lv_obj_set_size(bar, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
        lib.lv_obj_set_style_min_width(bar, lib.lv_pct(100), SEL)
        lib.lv_obj_set_style_radius(bar, 0, SEL)
        lib.lv_obj_set_style_border_width(bar, 0, SEL)
        lib.lv_obj_set_style_pad_all(bar, 8, SEL)
        lib.lv_obj_set_style_bg_color(bar, lib.lv_color_hex(0xE8E8E8), SEL)
        lib.lv_obj_set_flex_flow(bar, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(bar, lib.LV_FLEX_ALIGN_START, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        label = lib.lv_label_create(bar)
        lib.lv_label_set_text(label, text_bytes(title or ''))
        lib.lv_obj_set_flex_grow(label, 1)
        if on_close is not None:
            close = lib.lv_button_create(bar)
            lib.lv_obj_set_style_pad_all(close, 4, SEL)
            x = lib.lv_label_create(close)
            lib.lv_label_set_text(x, b'X')

    body = lib.lv_obj_create(panel)
    lib.lv_obj_set_style_radius(body, 0, SEL)
    lib.lv_obj_set_style_border_width(body, 0, SEL)
    lib.lv_obj_set_style_bg_opa(body, lib.LV_OPA_TRANSP, SEL)
    lib.lv_obj_set_flex_flow(body, lib.LV_FLEX_FLOW_COLUMN)
    lib.lv_obj_set_style_pad_all(body, 12, SEL)
    lib.lv_obj_set_style_pad_row(body, 8, SEL)
    lib.lv_obj_set_width(body, lib.LV_SIZE_CONTENT)
    lib.lv_obj_set_style_min_width(body, lib.lv_pct(100), SEL)
    lib.lv_obj_set_height(body, lib.LV_SIZE_CONTENT)
    if height:
        lib.lv_obj_set_flex_grow(body, 1)
    return backdrop, panel, body, close


class Handlers:
    """Python callbacks for plain LVGL objects (buttons inside dialogs)."""

    def __init__(self):
        self.natives = []

    def on(self, obj, code, callback):
        owner = _CallbackNode(callback, code)
        native = _Native(owner, obj, (code,))
        owner._native = native
        self.natives.append(native)
        return native

    def clear(self):
        for native in self.natives:
            native.node = None
        self.natives.clear()


from .base import _Native


class _CallbackNode:
    destroyed = False

    def __init__(self, callback, code):
        self.callback = callback
        self.code = code
        self._native = None

    def _lv_event(self, code, e):
        if code == self.code:
            self.callback(code, e)
