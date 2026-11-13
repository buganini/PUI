from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .textfield import _Editor, _ffi_text
from .base import *


class TextEdit(TextEditBinding, _Editor):
    """Plain multiline text, committed on blur; Enter inserts a newline."""
    expand_x_prio = expand_y_prio = 4
    _one_line = False

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
        lib.lv_obj_set_state(self.ui, lib.LV_STATE_DISABLED, bool(self.readonly))
        self._sync_text(prev)

    def _edited(self, value):
        self._input_text(value)

    def _commit(self):
        node = self.get_node()
        if node.ui is not None:
            node._commit_text(_ffi_text(node.ui))


TextEditor = TextEdit
