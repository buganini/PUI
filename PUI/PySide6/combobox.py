from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class ComboBox(QtBaseWidget):
    pui_terminal = False
    def __init__(
        self,
        editable: bool = False,
        index_model: _t.Binding[_t.Any] | None = None,
        text_model: _t.Binding[_t.Any] | None = None,
        *,
        disabled: bool = False,
        autoexpand: bool = True,
    ) -> None:
        super().__init__()
        self.combo_state = {'key': None, 'text': ''}
        self.editable = editable
        self.autoexpand = autoexpand
        self.disabled = disabled
        self.index_model = index_model
        self.text_model = text_model # ComboBox can be editable so the value is processed as text

    def update(self, prev):
        self.combo_state = prev.combo_state if prev else self.combo_state
        if prev and prev.ui:
            self.curr_index = prev.curr_index
            self.curr_text = prev.curr_text
            self.signal_connected = prev.signal_connected
            self.ui = prev.ui
        else:
            self.curr_index = Prop()
            self.curr_text = Prop()
            self.signal_connected = False
            self.ui = QtWidgets.QComboBox()
        if self.signal_connected:
            self.ui.currentIndexChanged.disconnect()
            self.ui.currentTextChanged.disconnect()
            self.signal_connected = False
        editor = self.ui.lineEdit() if self.ui.isEditable() else None
        self.editor_state = (editor.text(), editor.cursorPosition(),
                             editor.selectionStart(), len(editor.selectedText())) if editor else None
        self.ui.setEditable(self.editable)
        if self.editable and self.autoexpand:
            completer = self.ui.completer()
            if completer is None or not getattr(completer, '_pui_candidates', False):
                completer = QtWidgets.QCompleter(self.ui)
                completer.setModel(QtCore.QStringListModel(completer))
                completer._pui_candidates = True
                self.ui.setCompleter(completer)
            completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.UnfilteredPopupCompletion)
        elif self.editable:
            self.ui.setCompleter(None)
        if self.editable:
            editor = self.ui.lineEdit()
            if not getattr(editor, '_pui_completion', False):
                editor.textEdited.connect(lambda text: self._text_edited(text))
                editor._pui_completion = True
        self.ui.setDisabled(self.disabled)
        super().update(prev)

    def postSync(self):
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)

        if self.signal_connected:
            self.ui.currentIndexChanged.disconnect()
            self.ui.currentTextChanged.disconnect()

        editor = self.ui.lineEdit() if self.editable else None
        cursor = editor.cursorPosition() if editor is not None else None
        unchanged = self.ui.currentText() == text
        self.curr_index.set(index)
        if self.ui.currentIndex() != index:
            self.ui.setCurrentIndex(index)
        self.curr_text.set(text)
        if self.ui.currentText() != text:
            self.ui.setCurrentText(text)
        if editor is not None and unchanged:
            editor.setCursorPosition(cursor)
        if editor is not None and self.editor_state and self.editor_state[0] == text:
            _, cursor, start, length = self.editor_state
            if start >= 0 and length:
                editor.setSelection(start, length)
            else:
                editor.setCursorPosition(cursor)

        completer = self.ui.completer() if self.editable else None
        if completer is not None and getattr(completer, '_pui_candidates', False):
            labels = [str(c.text) for c in self.children]
            values = labels
            if completer.model().stringList() != values:
                completer.model().setStringList(values)
        self.signal_connected = True
        self.ui.currentIndexChanged.connect(self.on_currentIndexChanged)
        self.ui.currentTextChanged.connect(self.on_currentTextChanged)

    def _text_edited(self, text):
        node = self.get_node()
        event = PUIEvent()
        event.value = text
        node._input(event)
        node.get_node()._complete(text)

    def _complete(self, text):
        node = self.get_node()
        if not node.autoexpand or node.disabled:
            return
        completer = node.ui.completer()
        labels = [str(child.text) for child in node.children]
        completer.model().setStringList(labels)
        if completer.model().rowCount():
            completer.complete()
        else:
            completer.popup().hide()

    def on_currentIndexChanged(self, idx):
        if self.retired_by:
            return
        if self.index_model:
            self.index_model.value = idx
        if self.text_model:
            self.text_model.value = self.children[idx].value if 0 <= idx < len(self.children) else ""
        combobox_record_selection(self.children, idx, self.combo_state)
        e = PUIEvent()
        e.value = idx
        self._change(e)

    def on_currentTextChanged(self, text):
        if self.retired_by:
            return
        if not self.editable:
            return
        index = self.ui.currentIndex()
        if 0 <= index < len(self.children) and text == self.children[index].text:
            return
        combobox_set_text(self.index_model, self.text_model, text, self.combo_state)
        e = PUIEvent()
        e.value = text
        self._change(e)

    def addChild(self, idx, child):
        self.ui.insertItem(idx, child.text)

    def removeChild(self, idx, child):
        self.ui.removeItem(idx)

class ComboBoxItem(PUINode):
    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
        super().__init__()
        self.id(text)
        self.text = text
        if value is None:
            value = text
        self.value = value
