from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .base import FBase, FView, ft


class TextEdit(TextEditBinding, FBase):
    expand_x_prio = expand_y_prio = 4

    def __init__(
        self,
        model: _t.Binding[_t.Any],
        edit_model: _t.Binding[_t.Any] | None = None,
        *,
        placeholder: str | None = None,
        readonly: bool = False,
        wrap: bool = True,
    ) -> None:
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder
        self.readonly = readonly
        self.wrap = wrap
        self.editing = False
        if not wrap:
            raise NotImplementedError('Flet TextField does not support multiline text without soft wrapping')

    def _set_text(self, value):
        if self.ui.value != value:
            self.ui.value = value

    def update(self, prev):
        self.ui = prev.ui if prev is not None else ft.TextField(multiline=True, min_lines=4)
        self.ui.read_only = self.readonly
        self.ui.hint_text = self.placeholder
        self.ui.multiline, self.ui.shift_enter = True, False
        self.ui.on_change = self._edited
        self.ui.on_blur = self._blurred
        self.ui.on_focus = self._focused
        self.ui.on_submit = None
        self._sync_text(prev)
        super().update(prev)

    def _edited(self, event):
        self.get_node()._input_text(event.control.value)

    def on_change(self, event=None):
        # Flet's application commits its focused editor before button actions.
        self.get_node()._commit_text(self.ui.value)

    def _blurred(self, event):
        self.on_change(event)
        app = FView.application(self.get_node())
        if app is not None and app.focused_editor is not None and app.focused_editor.get_node() is self.get_node():
            app.focused_editor = None

    def _focused(self, event):
        app = FView.application(self.get_node())
        if app is not None:
            app.focused_editor = self.get_node()
