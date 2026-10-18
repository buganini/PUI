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
    ) -> None:
        super().__init__()
        self.combo_state = {'key': None, 'text': ''}
        self.editable = editable
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
        self.ui.setEditable(self.editable)
        self.ui.setDisabled(self.disabled)
        super().update(prev)

    def postSync(self):
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)

        if self.signal_connected:
            self.ui.currentIndexChanged.disconnect()
            self.ui.currentTextChanged.disconnect()

        if self.curr_index.set(index):
            self.ui.setCurrentIndex(index)

        if self.curr_text.set(text):
            self.ui.setCurrentText(text)

        self.signal_connected = True
        self.ui.currentIndexChanged.connect(self.on_currentIndexChanged)
        self.ui.currentTextChanged.connect(self.on_currentTextChanged)

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
