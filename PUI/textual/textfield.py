from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class TextField(TBase):
    _masked = False
    expand_x_prio = 3
    content_width = None
    def __init__(
        self,
        model: _t.Binding[_t.Any],
        edit_model: _t.Binding[_t.Any] | None = None,
        *,
        placeholder: str | None = None,
    ) -> None:
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder
        self.editing = False

    def update(self, prev):
        model_value = str(self.model.value)

        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if not self.editing and self.curr_value.set(model_value):
                with self.ui.prevent(widgets.Input.Changed):
                    self.ui.value = model_value
        else:
            self.ui = widgets.Input(password=self._masked)
            with self.ui.prevent(widgets.Input.Changed):
                self.ui.value = model_value
            self.curr_value = Prop(model_value)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        self.ui.puinode = self
        self.ui.placeholder = '' if self.placeholder is None else self.placeholder
        super().update(prev)

    def _tchanged(self, value): # editing
        node = self.get_node()
        node.editing = True
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)

    def _tsubmitted(self, value): # finish editing
        node = self.get_node()
        node.editing = False
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._change(e)


class MaskedField(TextField):
    """Single-line password editor with TextField binding and event semantics."""
    _masked = True
