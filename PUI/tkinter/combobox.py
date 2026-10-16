from .base import *


class ComboBox(TkBaseWidget):
    ttk_style = 'TCombobox'
    pui_terminal = False

    def __init__(self, editable=False, index_model=None, text_model=None, *, enabled=True):
        super().__init__()
        self.combo_state = {'key': None, 'text': ''}
        self.editable, self.index_model, self.text_model = editable, index_model, text_model
        self.enabled = enabled

    def update(self, prev):
        self.combo_state = prev.combo_state if prev else self.combo_state
        if prev and prev.ui is not None:
            self.ui, self.variable, self.notifications = prev.ui, prev.variable, prev.notifications
            self.variable.trace_remove('write', prev.trace_id)
            self.ui.unbind('<<ComboboxSelected>>', prev.selected_id)
        else:
            self.variable = tk.StringVar(self.tkparent.inner)
            self.ui = ttk.Combobox(self.tkparent.inner, textvariable=self.variable)
            self.notifications = {'after': None, 'skip': False, 'silent': False, 'text': ''}
        state = 'normal' if self.editable else 'readonly'
        self.ui.configure(state=state if self.enabled else 'disabled')
        self.trace_id = self.variable.trace_add('write', self.on_text)
        self.selected_id = self.ui.bind('<<ComboboxSelected>>', self.on_selected)
        super().update(prev)

    def postSync(self):
        self.ui.configure(values=[child.text for child in self.children])
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)
        self.notifications['silent'] = True
        try:
            if index >= 0:
                self.ui.current(index)
            self.variable.set(text)
        finally:
            self.notifications['silent'] = False

    def on_text(self, *args):
        node = self.get_node()
        if node.destroyed or node.notifications['silent'] or not node.editable:
            return
        node.notifications['text'] = node.variable.get()
        if node.notifications['after'] is None:
            node.notifications['after'] = node.ui.after_idle(node.notify_text)

    def notify_text(self):
        node = self.get_node()
        node.notifications['after'] = None
        if node.destroyed:
            return
        if node.notifications['skip']:
            node.notifications['skip'] = False
            return
        value = node.notifications['text']
        combobox_set_text(node.index_model, node.text_model, value, node.combo_state)
        event = PUIEvent()
        event.value = value
        node._change(event)

    def on_selected(self, event):
        node = self.get_node()
        if node.destroyed:
            return
        node.notifications['skip'] = node.notifications['after'] is not None
        index = node.ui.current()
        if node.index_model is not None:
            node.index_model.value = index
        if node.text_model is not None:
            node.text_model.value = node.children[index].value if 0 <= index < len(node.children) else ''
        combobox_record_selection(node.children, index, node.combo_state)
        e = PUIEvent()
        e.value = index
        node._change(e)

    def destroy(self, direct):
        if self.ui is not None:
            try:
                self.variable.trace_remove('write', self.trace_id)
                if self.notifications['after'] is not None:
                    self.ui.after_cancel(self.notifications['after'])
                    self.notifications['after'] = None
            except tk.TclError:
                pass
        super().destroy(direct)


class ComboBoxItem(PUINode):
    pui_terminal = True

    def __init__(self, text, value=None):
        super().__init__()
        self.id(text)
        self.text, self.value = text, text if value is None else value
