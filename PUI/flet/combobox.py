from __future__ import annotations
from .. import _typing as _t
from .base import *
from .completion import Completion


class ComboBox(FBase):
    expand_x_prio, expand_y_prio = 4, 0
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
        if self.editable:
            self.completion = (prev.completion if prev and prev.editable else Completion(self))
            self.completion.node = self
            self.ui = self.completion.editor
        else:
            if prev and prev.editable:
                prev.completion.close()
            self.ui = prev.ui if prev and not prev.editable else ft.Dropdown()
            self.ui.editable = False
            self.ui.on_select = self.on_select
        super().update(prev)
        self.ui.disabled = self.flet_params.get('disabled', self.disabled)
        if self.editable:
            self.shell.content = self.completion.control
            # Like TextField, expand within a Row rather than handing Flutter an
            # unconstrained editor. Explicit PUI widths/weights still take precedence.
            if (self.layout_width is None and self.layout_weight is None
                    and getattr(self.fparent, 'container_x', False)):
                self.shell.expand = True
            if prev and prev.autoexpand and not self.autoexpand:
                self.completion.requested = False

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def postSync(self):
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)
        if self.editable:
            if self.ui.value != text:
                self.ui.value = text
            self.completion.refresh()
        else:
            for i, item in enumerate(self.children):
                item.ui.key, item.ui.text = str(i), item.text
            self.ui.options = [child.ui for child in self.children]
            self.ui.value = str(index) if index >= 0 else None
            self.ui.text = self.children[index].text if index >= 0 else ''

    def on_select(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None or node.ui.disabled:
            return
        try:
            index = int(node.ui.value)
        except (TypeError, ValueError):
            index = -1
        node._select(index)

    def _select(self, index):
        if not 0 <= index < len(self.children):
            index = -1
        if self.index_model is not None:
            self.index_model.value = index
        if self.text_model is not None:
            self.text_model.value = self.children[index].value if index >= 0 else ''
        combobox_record_selection(self.children, index, self.combo_state)
        if self.editable:
            self.ui.value = str(self.children[index].text) if index >= 0 else ''
        e = PUIEvent()
        e.value = index
        self._change(e)

    def on_text_change(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None or not node.editable:
            return
        if node.ui.disabled:
            return
        text = node.ui.value or ''
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
