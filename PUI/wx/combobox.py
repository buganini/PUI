from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
from .completion import Completion

class ComboBox(WxBaseWidget):
    pui_terminal = False
    def __init__(
        self,
        editable: bool = False,
        *,
        index_model: _t.Binding[_t.Any] | None = None,
        text_model: _t.Binding[_t.Any] | None = None,
        edit_model: _t.Binding[_t.Any] | None = None,
        disabled: bool = False,
        autoexpand: bool = True,
    ) -> None:
        self._internal_tag = str(bool(editable))
        super().__init__()
        self.edit_model = edit_model
        self.combo_state = {'key': None, 'text': ''}
        self.editable = editable
        self.autoexpand = autoexpand
        self.disabled = disabled
        self.index_model = index_model
        self.text_model = text_model

    def update(self, prev):
        self.combo_state = prev.combo_state if prev else self.combo_state
        if prev and prev.ui:
            self.curr_index = prev.curr_index
            self.curr_text = prev.curr_text
            self.ui = prev.ui
            self.completion = prev.completion
            self.completion.node = self
            self.ui.Unbind(wx.EVT_COMBOBOX)
            self.ui.Unbind(wx.EVT_TEXT)
        else:
            self.curr_index = Prop()
            self.curr_text = Prop()
            self.ui = wx.ComboBox(getWindow(self.parent), choices=[], style=0 if self.editable else wx.CB_READONLY)
            self.completion = Completion(self)
        self.ui.Bind(wx.EVT_COMBOBOX, self._combobox)
        self.ui.Bind(wx.EVT_TEXT, self._text)

        super().update(prev)

    def postSync(self):
        # Native choices must follow updated labels as well as insertions/removals.
        if self.ui.GetItems() != [c.text for c in self.children]:
            self.ui.SetItems([c.text for c in self.children])
        self.ui.SetEditable(self.editable)
        self.ui.Enable(not self.disabled)
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)
        if self.ui.GetSelection() != index or self.ui.GetValue() != text:
            self.ui.SetSelection(index)
            if self.editable:
                self.ui.ChangeValue(text)
        self.curr_index.set(index)
        self.curr_text.set(text)
        self.completion.refresh()

    def _combobox(self, *args, **kwargs):
        node = self.get_node()
        idx = node.ui.GetSelection()
        if node.index_model is not None:
            node.index_model.value = idx
        if node.text_model is not None:
            node.text_model.value = node.children[idx].value if 0 <= idx < len(node.children) else ""
        combobox_record_selection(node.children, idx, node.combo_state)
        e = PUIEvent()
        e.value = idx
        node._change(e)

    def _text(self, *args, **kwargs):
        node = self.get_node()
        if not node.editable:
            return
        text = node.ui.GetValue()
        index = node.ui.GetSelection()
        if 0 <= index < len(node.children) and text == node.children[index].text:
            return
        node.completion.refresh(show=True)
        combobox_set_text(node.index_model, node.text_model, text, node.combo_state)
        e = PUIEvent()
        e.value = text
        if node.edit_model is not None:
            node.edit_model.value = text
        node._input(e)
        node._change(e)

    def destroy(self, direct):
        if hasattr(self, "completion"):
            self.completion.destroy()
        super().destroy(direct)

    def addChild(self, idx, child):
        self.ui.Insert(child.text, idx)

    def removeChild(self, idx, child):
        self.ui.Delete(idx)

class ComboBoxItem(PUINode):
    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
        super().__init__()
        self.id(text)
        self.text = text
        if value is None:
            value = text
        self.value = value
