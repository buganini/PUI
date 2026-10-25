from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .base import TBase, widgets


class _Editor(widgets.TextArea):
    def on_text_area_changed(self, event):
        if event.text_area is self:
            self.puinode.get_node()._input_text(self.text)
            event.stop()

    def on_blur(self, event):
        self.puinode.get_node()._commit_text(self.text)


class TextEdit(TextEditBinding, TBase):
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

    def _set_text(self, value):
        if self.ui.text != value:
            with self.ui.prevent(widgets.TextArea.Changed):
                self.ui.load_text(value)

    def update(self, prev):
        self.ui = prev.ui if prev is not None else _Editor(tab_behavior='focus')
        self.ui.puinode = self
        self.ui.read_only = self.readonly
        self.ui.soft_wrap = self.wrap
        self.ui.placeholder = self.placeholder or ''
        self._sync_text(prev)
        super().update(prev)
