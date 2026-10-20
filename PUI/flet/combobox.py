from __future__ import annotations
from .. import _typing as _t
from .base import *


class ComboBox(FBase):
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
        super().__init__()
        self.edit_model = edit_model
        self.combo_state = {'key': None, 'text': ''}
        self.editable, self.index_model, self.text_model = editable, index_model, text_model
        self.autoexpand = autoexpand
        self.disabled = disabled

    def update(self, prev):
        self.combo_state = prev.combo_state if prev else self.combo_state
        self.ui = prev.ui if prev and prev.ui is not None else ft.Dropdown()
        self.ui.editable = self.editable
        self.ui.enable_filter = False
        self.ui.enable_search = self.autoexpand if self.editable else True
        self.ui.on_select = self.on_select
        self.ui.on_text_change = self.on_text_change
        super().update(prev)
        self.ui.disabled = self.flet_params.get('disabled', self.disabled)

    def addChild(self, idx, child):
        self.ui.options.insert(idx, child.ui)

    def removeChild(self, idx, child):
        self.ui.options.pop(idx)

    def postSync(self):
        for i, item in enumerate(self.children):
            item.ui.key, item.ui.text = str(i), item.text
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)
        self.ui.value = str(index) if index >= 0 else None
        self.ui.text = self.children[index].text if index >= 0 else text if self.editable else ''

    def on_select(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        try:
            index = int(node.ui.value)
        except (TypeError, ValueError):
            index = -1
        if not 0 <= index < len(node.children):
            index = -1
        if node.index_model is not None:
            node.index_model.value = index
        if node.text_model is not None:
            node.text_model.value = node.children[index].value if index >= 0 else ''
        combobox_record_selection(node.children, index, node.combo_state)
        e = PUIEvent()
        e.value = index
        node._change(e)

    def on_text_change(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None or not node.editable:
            return
        text = node.ui.text or ''
        if node.ui.value is not None:
            try:
                if node.children[int(node.ui.value)].text == text:
                    return  # Native selected-label updates preserve the item's value.
            except (IndexError, ValueError):
                pass
        combobox_set_text(node.index_model, node.text_model, text, node.combo_state)
        e = PUIEvent()
        e.value = text
        if node.edit_model is not None:
            node.edit_model.value = text
        node._input(e)
        node._change(e)


class ComboBoxItem(PUINode):
    pui_terminal = True

    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
        super().__init__()
        self.id(text)
        self.text, self.value = text, text if value is None else value

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.DropdownOption()
        self.ui.text = self.text
        super().update(prev)
