from __future__ import annotations
from .. import _typing as _t
from ..common import checkbox_get, checkbox_set
from .base import *


class Checkbox(LBaseWidget):
    _default_size = ('content', 'content')
    _always_clickable = True
    _lv_events = (lib.LV_EVENT_VALUE_CHANGED,)

    def __init__(self, text: _t.Any, model: _t.Binding[_t.Any], value: _t.Any = None, *,
                 disabled: bool = False) -> None:
        super().__init__()
        self.text = str(text)
        self.model = model
        self.value = text if value is None else value
        self.disabled = disabled

    def create(self, parent):
        return lib.lv_checkbox_create(parent)

    def configure(self, prev):
        lib.lv_checkbox_set_text(self.ui, text_bytes(self.text))
        lib.lv_obj_set_state(self.ui, lib.LV_STATE_CHECKED, bool(checkbox_get(self.model, self.value)))
        lib.lv_obj_set_state(self.ui, lib.LV_STATE_DISABLED, bool(self.disabled))

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_VALUE_CHANGED:
            checkbox_set(self.model, bool(lib.lv_obj_has_state(self.ui, lib.LV_STATE_CHECKED)), self.value)
        else:
            super()._lv_event(code, e)
