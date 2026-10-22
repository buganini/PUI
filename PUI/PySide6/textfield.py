from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class TextField(QtBaseWidget):
    expand_x_prio = 4
    _masked = False
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
            self.ui.node = self
            self.ui.textChanged.disconnect()
            if not self.editing and self.curr_value.set(model_value):
                self.ui.setText(model_value)
            self.ui.editingFinished.disconnect()
        else:
            self.ui = QtWidgets.QLineEdit()
            if self._masked:
                self.ui.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            self.ui.setFocusPolicy(QtCore.Qt.ClickFocus | QtCore.Qt.NoFocus)
            self.ui.node = self
            self.ui.setText(model_value)
            self.curr_value = Prop(model_value)
        self.ui.textChanged.connect(self.on_textchanged)
        self.ui.editingFinished.connect(self.on_editing_finished)
        self.ui.setPlaceholderText('' if self.placeholder is None else self.placeholder)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_editing_finished(self): # finish editing
        node = self.get_node()
        node.editing = False
        value = self.ui.text()
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        model_value = str(self.model.value)
        self.ui.blockSignals(True)
        self.ui.setText(model_value)
        self.ui.blockSignals(False)
        e = PUIEvent()
        e.value = value
        self._change(e)
        node.ui.clearFocus()

    def on_textchanged(self): # editing
        node = self.get_node()
        node.editing = True
        value = self.ui.text()
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)


class MaskedField(TextField):
    """Single-line password editor with TextField binding and event semantics."""
    _masked = True
