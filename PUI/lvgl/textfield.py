from __future__ import annotations
from .. import _typing as _t
from .base import *

_focused = None


def commit_focused(clicked=None):
    """Clicking elsewhere ends editing like a focus change on desktop toolkits."""
    global _focused
    field = _focused
    if field is None or field is clicked:
        return
    _focused = None
    field = field.get_node()
    if not field.destroyed and field.ui is not None:
        field._commit()


def _ffi_text(obj):
    text = lib.lv_textarea_get_text(obj)
    return ffi.string(text).decode('utf-8', 'replace') if text != ffi.NULL else ''


class _Editor(LBaseWidget):
    _always_clickable = True
    _lv_events = (lib.LV_EVENT_VALUE_CHANGED, lib.LV_EVENT_READY,
                  lib.LV_EVENT_FOCUSED, lib.LV_EVENT_DEFOCUSED)
    _one_line = True
    _masked = False

    def create(self, parent):
        obj = lib.lv_textarea_create(parent)
        lib.lv_textarea_set_one_line(obj, self._one_line)
        lib.lv_textarea_set_password_mode(obj, self._masked)
        return obj

    def _set_text(self, value):
        store = self._native.store
        if _ffi_text(self.ui) != value:
            store['updating'] = True
            try:
                lib.lv_textarea_set_text(self.ui, value.encode('utf-8'))
            finally:
                store['updating'] = False

    def _lv_event(self, code, e):
        global _focused
        store = self._native.store
        if code == lib.LV_EVENT_VALUE_CHANGED:
            if not store.get('updating'):
                self._edited(_ffi_text(self.ui))
        elif code == lib.LV_EVENT_FOCUSED:
            _focused = self
        elif code in (lib.LV_EVENT_READY, lib.LV_EVENT_DEFOCUSED):
            if _focused is not None and _focused.get_node() is self:
                _focused = None
            self._commit()
        else:
            super()._lv_event(code, e)

    def _preClicked(self):
        commit_focused(self)


class TextField(_Editor):
    expand_x_prio = 4
    _default_size = (None, 'content')

    def __init__(self, model: _t.Binding[_t.Any], edit_model: _t.Binding[_t.Any] | None = None, *,
                 placeholder: str | None = None) -> None:
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder

    def configure(self, prev):
        store = self._native.store
        lib.lv_textarea_set_placeholder_text(self.ui, text_bytes(self.placeholder or ''))
        value = str(self.model.value)
        if not store.get('editing'):
            if store.get('model') != value:
                self._set_text(value)
                store['model'] = value
            if self.edit_model is not None and self.edit_model.value != value:
                # Defer: a state write here would redraw during reconciliation.
                edit_model = self.edit_model
                runtime.post(lambda: setattr(edit_model, 'value', value))

    def _edited(self, value):
        node = self.get_node()
        node._native.store['editing'] = True
        if node.edit_model is not None:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        node._input(e)

    def _commit(self):
        node = self.get_node()
        store = node._native.store if node._native is not None else None
        if store is None or not store.get('editing'):
            return
        value = _ffi_text(node.ui)
        store['editing'] = False
        node.model.value = value
        committed = str(node.model.value)
        if node.ui is not None:
            node._set_text(committed)
            store['model'] = committed
        if node.edit_model is not None:
            node.edit_model.value = committed
        e = PUIEvent()
        e.value = value
        node._change(e)


class MaskedField(TextField):
    """Single-line password editor with TextField binding and event semantics."""
    _masked = True


PasswordField = MaskedField
