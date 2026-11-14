from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .textfield import _Editor, _ffi_text
from .base import *


class TextEdit(TextEditBinding, _Editor):
    """Plain multiline text, committed on blur; Enter inserts a newline."""
    expand_x_prio = expand_y_prio = 4
    _one_line = False
    _lv_events = _Editor._lv_events + (lib.LV_EVENT_INSERT, lib.LV_EVENT_SIZE_CHANGED)

    def __init__(self, model: _t.Binding[_t.Any], edit_model: _t.Binding[_t.Any] | None = None, *,
                 placeholder: str | None = None, readonly: bool = False, wrap: bool = True) -> None:
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder
        self.readonly = readonly
        self.wrap = wrap
        self.editing = False

    def configure(self, prev):
        lib.lv_textarea_set_placeholder_text(self.ui, text_bytes(self.placeholder or ''))
        # Read-only text stays focusable, selectable and scrollable; inserts
        # are dropped in _lv_event instead of disabling the widget.
        self._sync_text(prev)
        self._apply_wrap()

    def _apply_wrap(self):
        label = lib.lv_textarea_get_label(self.ui)
        if self.wrap:
            lib.lv_label_set_long_mode(label, lib.LV_LABEL_LONG_MODE_WRAP)
            lib.lv_obj_set_width(label, lib.lv_obj_get_content_width(self.ui))
        else:
            lib.lv_label_set_long_mode(label, lib.LV_LABEL_LONG_MODE_CLIP)
            lib.lv_obj_set_width(label, lib.LV_SIZE_CONTENT)

    def _lv_event(self, code, e):
        node = self.get_node()
        if code == lib.LV_EVENT_INSERT:
            if node.readonly and not self._native.store.get('updating'):
                lib.lv_textarea_set_insert_replace(self.ui, b'')
        elif code == lib.LV_EVENT_SIZE_CHANGED:
            node._apply_wrap()
            super()._lv_event(code, e)
        else:
            super()._lv_event(code, e)

    def _edited(self, value):
        self._input_text(value)

    def _commit(self):
        node = self.get_node()
        if node.ui is not None:
            node._commit_text(_ffi_text(node.ui))


TextEditor = TextEdit
