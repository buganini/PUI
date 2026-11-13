from __future__ import annotations
from .. import _typing as _t
from ..common import combobox_get, combobox_record_selection
from .base import *


class ComboBox(LBaseWidget):
    """Drop-down list of ComboBoxItem children (editing is not supported)."""
    pui_terminal = False
    _always_clickable = True
    _lv_events = (lib.LV_EVENT_VALUE_CHANGED,)

    def __init__(self, editable: bool = False, *, index_model: _t.Binding[_t.Any] | None = None,
                 text_model: _t.Binding[_t.Any] | None = None, edit_model: _t.Binding[_t.Any] | None = None,
                 disabled: bool = False, autoexpand: bool = True) -> None:
        super().__init__()
        self.editable = editable
        self.index_model = index_model
        self.text_model = text_model
        self.edit_model = edit_model
        self.disabled = disabled
        self.autoexpand = autoexpand
        self.combo_state = {'key': None, 'text': ''}

    def adopt(self, prev):
        self.combo_state = prev.combo_state

    def create(self, parent):
        return lib.lv_dropdown_create(parent)

    def configure(self, prev):
        lib.lv_obj_set_state(self.ui, lib.LV_STATE_DISABLED, bool(self.disabled))

    def postSync(self):
        if self.ui is None:
            return
        store = self._native.store
        items = [c for c in self.children if isinstance(c, ComboBoxItem)]
        options = '\n'.join(str(c.text).replace('\n', ' ') for c in items)
        index, text = combobox_get(items, self.index_model, self.text_model, self.editable, self.combo_state)
        store['syncing'] = True
        if store.get('options') != options:
            lib.lv_dropdown_set_options(self.ui, options.encode('utf-8'))
            store['options'] = options
        if index is not None and 0 <= index < len(items):
            lib.lv_dropdown_set_selected(self.ui, index)
            lib.lv_dropdown_set_text(self.ui, ffi.NULL)
        else:
            # No selection (or free text): show the text instead of item 0.
            lib.lv_dropdown_set_text(self.ui, text_bytes(text or ''))
        store['syncing'] = False
        super().postSync()

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_VALUE_CHANGED:
            if self._native.store.get('syncing'):
                return
            items = [c for c in self.children if isinstance(c, ComboBoxItem)]
            idx = lib.lv_dropdown_get_selected(self.ui)
            if self.index_model is not None:
                self.index_model.value = idx
            if self.text_model is not None:
                self.text_model.value = items[idx].value if 0 <= idx < len(items) else ''
            combobox_record_selection(items, idx, self.combo_state)
            ev = PUIEvent()
            ev.value = idx
            self._change(ev)
        else:
            super()._lv_event(code, e)


class ComboBoxItem(PUINode):
    pui_terminal = True

    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
        super().__init__()
        self.id(text)
        self.text = text
        self.value = text if value is None else value


from ..fontcombobox import FontComboBoxMixin


class FontComboBox(FontComboBoxMixin, ComboBox):
    """LVGL renders only its built-in Montserrat bitmap fonts."""
    @staticmethod
    def default_fonts():
        return ('Montserrat',)

    def font_item(self, name):
        ComboBoxItem(name)
