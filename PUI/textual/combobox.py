from __future__ import annotations
from .. import _typing as _t
from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.widgets import Input, OptionList, Select
from textual.widgets.option_list import Option
from .base import *


class _Editor(Input):
    BINDINGS = [Binding('down', 'candidate_down', show=False, priority=True),
                Binding('up', 'candidate_up', show=False, priority=True),
                Binding('enter', 'candidate_accept', show=False, priority=True),
                Binding('escape', 'candidate_close', show=False, priority=True)]

    def action_candidate_down(self):
        self.parent.move_candidate(1)

    def action_candidate_up(self):
        self.parent.move_candidate(-1)

    def action_candidate_accept(self):
        self.parent.accept()

    def action_candidate_close(self):
        self.parent.close_candidates()


class _Candidates(OptionList, can_focus=False):
    pass


class _Combo(containers.Vertical):
    DEFAULT_CSS = '''
    _Combo { height: 3; min-height: 3; }
    _Combo > _Editor { width: 1fr; }
    _Combo > Select { width: 1fr; }
    _Combo > _Candidates {
        display: none; height: auto; max-height: 10;
        width: 1fr; overlay: screen; constrain: none inside;
        background: $surface; color: $foreground; border: tall $border;
    }
    '''

    def __init__(self):
        super().__init__()
        self.editor = _Editor()
        self.choices = _Candidates()
        self.select = Select([], allow_blank=True)
        self.indices = []
        self.all_choices = False
        self.signature = None
        self.labels = None

    def compose(self):
        yield self.editor
        yield self.select
        yield self.choices

    def close_candidates(self):
        self.choices.display = False
        self.all_choices = False
        self.choices.highlighted = None

    def candidates(self, show=False, all_choices=None):
        node = self.puinode
        if all_choices is not None:
            self.all_choices = all_choices
        if not node.editable or (not node.autoexpand and not self.all_choices) or node.disabled:
            self.close_candidates()
            return
        if not show and not self.choices.display:
            return
        self.indices = combobox_matches([c.text for c in node.children], '' if self.all_choices else self.editor.value)
        signature = [(i, node.children[i].key, str(node.children[i].text)) for i in self.indices]
        if show or signature != self.signature:
            self.choices.clear_options()
            self.choices.add_options([Option(Text(str(node.children[i].text))) for i in self.indices])
            self.choices.highlighted = None
            self.signature = signature
        self.choices.display = bool(self.indices)

    def move_candidate(self, step):
        if not self.choices.display:
            self.candidates(show=True, all_choices=not self.puinode.autoexpand)
        if not self.indices or not self.choices.display:
            return
        current = self.choices.highlighted
        self.choices.highlighted = ((current+step) % len(self.indices) if current is not None
                                    else (0 if step == 1 else len(self.indices)-1))

    def accept(self):
        current = self.choices.highlighted
        if self.choices.display and current is not None:
            self.puinode._select(self.indices[current])
        else:
            self.puinode._submit(self.editor.value)
        self.close_candidates()

    def on_input_changed(self, event: Input.Changed):
        event.stop()
        if self.puinode.disabled or not self.puinode.editable:
            return
        self.candidates(show=True, all_choices=False)
        self.puinode._edit(event.value)

    def on_input_submitted(self, event: Input.Submitted):
        event.stop()
        self.accept()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        if (self.choices.display and event.option_index < len(self.indices)
                and self.choices.get_option_at_index(event.option_index) is event.option):
            self.puinode._select(self.indices[event.option_index])
            self.close_candidates()
            self.editor.focus(scroll_visible=False)

    def on_select_changed(self, event: Select.Changed):
        event.stop()
        if not self.puinode.editable and not self.puinode.disabled:
            self.puinode._select(-1 if event.value is Select.NULL else event.value)

    def on_descendant_blur(self, event: events.DescendantBlur):
        self.call_after_refresh(self._check_focus)

    def _check_focus(self):
        if self.app.focused is not self.editor:
            self.close_candidates()


class ComboBox(TBase):
    pui_terminal = False
    expand_x_prio = 3
    content_width = None

    def __init__(self, editable: bool = False,
                 index_model: _t.Binding[_t.Any] | None = None,
                 text_model: _t.Binding[_t.Any] | None = None, *,
                 disabled: bool = False, autoexpand: bool = True) -> None:
        super().__init__()
        self.editable, self.disabled, self.autoexpand = editable, disabled, autoexpand
        self.index_model, self.text_model = index_model, text_model
        self.combo_state = {'key': None, 'text': ''}

    def update(self, prev):
        if prev is not None:
            self.ui, self.combo_state = prev.ui, prev.combo_state
        else:
            self.ui = _Combo()
        self.ui.puinode = self
        self.ui.disabled = self.disabled
        self.ui.editor.display = self.editable
        self.ui.select.display = not self.editable
        super().update(prev)

    def addChild(self, idx, child): pass
    def removeChild(self, idx, child): pass

    def postSync(self):
        self.ui.call_after_refresh(self._sync_control)

    def _sync_control(self):
        node = self.get_node()
        if node is not self:
            return node._sync_control()
        if self.destroyed or not self.ui.is_mounted:
            return
        labels = [str(c.text) for c in self.children]
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)
        with self.ui.select.prevent(Select.Changed):
            if self.ui.labels != labels:
                self.ui.select.set_options([(Text(label), i) for i, label in enumerate(labels)])
                self.ui.labels = labels
            self.ui.select.value = index if index >= 0 else Select.NULL
        with self.ui.editor.prevent(Input.Changed):
            if self.ui.editor.value != text:
                self.ui.editor.value = text
        self.ui.candidates()

    def _edit(self, text):
        combobox_set_text(self.index_model, self.text_model, text, self.combo_state)
        event = PUIEvent(); event.value = text
        self._input(event)

    def _submit(self, text):
        self._edit(text)
        event = PUIEvent(); event.value = text
        self._change(event)

    def _select(self, index):
        if self.disabled:
            return
        if self.index_model is not None:
            self.index_model.value = index
        value = self.children[index].value if 0 <= index < len(self.children) else ''
        if self.text_model is not None:
            self.text_model.value = value
        combobox_record_selection(self.children, index, self.combo_state)
        with self.ui.editor.prevent(Input.Changed):
            self.ui.editor.value = str(self.children[index].text) if index >= 0 else ''
        event = PUIEvent(); event.value = index
        self._change(event)


class ComboBoxItem(PUINode):
    pui_terminal = True

    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
        super().__init__()
        self.id(text)
        self.text, self.value = text, text if value is None else value


Combobox = ComboBox
ComboboxItem = ComboBoxItem
