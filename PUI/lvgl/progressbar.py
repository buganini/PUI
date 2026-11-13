from __future__ import annotations
from .. import _typing as _t
from .base import *


class ProgressBar(LBaseWidget):
    expand_x_prio = 1

    def __init__(self, progress: _t.Number = 0, maximum: _t.Number = 1) -> None:
        super().__init__()
        self.progress = progress * 100
        self.maximum = maximum * 100

    def create(self, parent):
        return lib.lv_bar_create(parent)

    def configure(self, prev):
        obj = self.ui
        busy = lib.lv_anim_get(obj, lib._pui_anim_busy_cb) != ffi.NULL
        if self.maximum <= 0:
            # Indeterminate: sweep a range indicator back and forth.
            if not busy:
                lib.lv_bar_set_range(obj, 0, 100)
                lib.lv_bar_set_mode(obj, lib.LV_BAR_MODE_RANGE)
                anim = ffi.new('lv_anim_t *')
                lib.lv_anim_init(anim)
                lib.lv_anim_set_var(anim, obj)
                lib.lv_anim_set_exec_cb(anim, lib._pui_anim_busy_cb)
                lib.lv_anim_set_values(anim, 0, 75)
                lib.lv_anim_set_duration(anim, 1000)
                lib.lv_anim_set_reverse_duration(anim, 1000)
                lib.lv_anim_set_repeat_count(anim, lib.LV_ANIM_REPEAT_INFINITE)
                lib.lv_anim_start(anim)
            return
        if busy:
            lib.lv_anim_delete(obj, lib._pui_anim_busy_cb)
            lib.lv_bar_set_mode(obj, lib.LV_BAR_MODE_NORMAL)
            lib.lv_bar_set_start_value(obj, 0, lib.LV_ANIM_OFF)
        lib.lv_bar_set_range(obj, 0, int(self.maximum))
        lib.lv_bar_set_value(obj, int(self.progress), lib.LV_ANIM_OFF)
