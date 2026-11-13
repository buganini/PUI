from __future__ import annotations
from ..color import rgb_color
from .. import _typing as _t
from .. import *

try:
    from .liblvgl import ffi, lib
except ImportError:
    raise ImportError(
        "PUI.lvgl native extension not built. "
        "Run: python PUI/lvgl/build_lvgl_cffi.py"
    )


class LPUIView(PUIView):
    pui_virtual = True

    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    def __init__(self, *args):
        super().__init__(*args)
        self._timer = None

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating:
            return
        self.sync()

    def destroy(self, direct):
        self.destroyed = True
        self.dirty = self.updating = False
        super().destroy(direct)


class LBaseWidget(PUINode):
    pui_terminal = True

    def _observe_size(self):
        return None

    def get_poster(self) -> _t.Poster:
        from ..poster import make_poster
        app = self
        while app.parent is not app:
            app = app.parent
        return make_poster(app._post_command, app._post_timer)

    @property
    def lvparent(self):
        parent = self.parent
        while parent is not None:
            if isinstance(parent, LBaseWidget) and parent.ui is not None:
                return parent
            if isinstance(parent, LPUIView) and parent.ui is not None:
                return parent
            if parent is parent.parent:
                return None
            parent = parent.parent
        return None

    @property
    def lv_parent_obj(self):
        p = self.lvparent
        if p is None:
            return lib.pui_lvgl_screen_active()
        return p.inner

    @property
    def inner(self):
        return self.ui

    @property
    def outer(self):
        return self.ui

    def destroy(self, direct):
        self.destroyed = True
        if self._event_descriptor is not None and self.ui is not None:
            lib.pui_lv_obj_remove_event_cb(self.ui, self._event_descriptor)
            self._event_descriptor = None
        if direct and self.ui is not None:
            lib.pui_lv_obj_delete(self.ui)
        self.ui = None
        super().destroy(direct)

    def __init__(self):
        super().__init__()
        self._event_descriptor = None

    def _setup_events(self):
        if self._event_descriptor is not None:
            lib.pui_lv_obj_remove_event_cb(self.ui, self._event_descriptor)
            self._event_descriptor = None
        if self.ui is not None:
            handle = ffi.new_handle(self)
            self._event_handle = handle
            self._event_descriptor = lib.pui_lv_obj_add_event_cb(
                self.ui, lib._pui_event_cb, handle)

    def update(self, prev):
        if prev and prev.ui is not None:
            if prev._event_descriptor is not None:
                lib.pui_lv_obj_remove_event_cb(prev.ui, prev._event_descriptor)
                prev._event_descriptor = None

        self._apply_styles()
        self._setup_events()
        super().update(prev)

    def _apply_styles(self):
        if self.ui is None:
            return
        obj = self.ui
        if self.layout_width is not None:
            lib.pui_lv_obj_set_width(obj, self.layout_width)
        if self.layout_height is not None:
            lib.pui_lv_obj_set_height(obj, self.layout_height)
        if self._minimum_size('x') is not None:
            lib.pui_lv_obj_set_min_width(obj, self._minimum_size('x'))
        if self._minimum_size('y') is not None:
            lib.pui_lv_obj_set_min_height(obj, self._minimum_size('y'))
        if self.layout_weight is not None:
            lib.pui_lv_obj_set_flex_grow(obj, self.layout_weight)
        if self.layout_padding is not None:
            top, right, bottom, left = self.layout_padding
            lib.pui_lv_obj_set_style_pad(obj, top, right, bottom, left)
        if self.style_color is not None:
            lib.pui_lv_obj_set_style_text_color(obj, self.style_color & 0xFFFFFF)
        if self.style_bgcolor is not None:
            lib.pui_lv_obj_set_style_bg_color(obj, self.style_bgcolor & 0xFFFFFF)
        if self.style_fontsize is not None:
            lib.pui_lv_obj_set_style_text_font_size(obj, self.style_fontsize)
        if not self._visible:
            lib.pui_lv_obj_set_hidden(obj, 1)
        else:
            lib.pui_lv_obj_set_hidden(obj, 0)


# ---- CFFI event callback ----

@ffi.def_extern()
def _pui_event_cb(event_code, user_data):
    try:
        node = ffi.from_handle(user_data)
    except Exception:
        return
    if event_code == lib.PUI_EVENT_CLICKED:
        node._clicked()
    elif event_code == lib.PUI_EVENT_VALUE_CHANGED:
        if hasattr(node, '_value_changed'):
            node._value_changed()


@ffi.def_extern()
def _pui_timer_cb(user_data):
    try:
        cb = ffi.from_handle(user_data)
    except Exception:
        return
    cb()
