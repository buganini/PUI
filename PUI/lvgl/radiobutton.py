from __future__ import annotations
from .. import _typing as _t
from .base import *


class RadioButton(LBaseWidget):
    _default_size = ('content', 'content')
    _always_clickable = True

    def __init__(self, text: _t.Any, value: _t.Any, model: _t.Binding[_t.Any], *,
                 disabled: bool = False) -> None:
        super().__init__()
        self.text = str(text)
        self.value = value
        self.model = model
        self.disabled = disabled

    def create(self, parent):
        obj = lib.lv_checkbox_create(parent)
        lib.lv_obj_set_style_radius(obj, lib.LV_RADIUS_CIRCLE, lib.LV_PART_INDICATOR)
        lib.lv_obj_set_style_bg_image_src(obj, ffi.NULL, lib.LV_PART_INDICATOR | lib.LV_STATE_CHECKED)
        return obj

    def configure(self, prev):
        lib.lv_checkbox_set_text(self.ui, text_bytes(self.text))
        self._show_checked()
        lib.lv_obj_set_state(self.ui, lib.LV_STATE_DISABLED, bool(self.disabled))

    def _show_checked(self):
        lib.lv_obj_set_state(self.ui, lib.LV_STATE_CHECKED, self.model.value == self.value)

    def _clicked(self, e=None, *args, **kwargs):
        node = self.get_node()
        # The native checkbox toggles itself; a radio button only selects.
        node.model.value = node.value
        if node.ui is not None:
            node._show_checked()
        super()._clicked(e, *args, **kwargs)


Radio = RadioButton
