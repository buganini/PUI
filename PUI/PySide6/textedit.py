from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .base import QtBaseWidget, QtCore, QtWidgets


class _Editor(QtWidgets.QPlainTextEdit):
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.node._commit_text(self.toPlainText())


class TextEdit(TextEditBinding, QtBaseWidget):
    """Plain multiline text, committed on blur; Enter inserts a newline."""
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
        if self.ui.toPlainText() != value:
            blocker = QtCore.QSignalBlocker(self.ui)
            self.ui.setPlainText(value)
            del blocker

    def update(self, prev):
        if prev is not None:
            self.ui = prev.ui
            self.ui.textChanged.disconnect()
        else:
            self.ui = _Editor()
            self.ui.setTabChangesFocus(True)
        self.ui.node = self
        self.ui.setReadOnly(self.readonly)
        self.ui.setPlaceholderText(self.placeholder or '')
        self.ui.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth if self.wrap
                                else QtWidgets.QPlainTextEdit.NoWrap)
        self._sync_text(prev)
        self.ui.textChanged.connect(lambda: self.ui.node._input_text(self.ui.toPlainText()))
        super().update(prev)
