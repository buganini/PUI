from .. import *
from .base import *


class TextField(TkBaseWidget):
    ttk_style = "TEntry"
    _masked = False
    grid_weight_x = 1
    grid_sticky = 'ew'

    def __init__(self, model, edit_model=None, *, placeholder=None):
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        # Tk 8.6 Entry has no native placeholder; accept it for API compatibility.
        self.placeholder = placeholder
        self.editing = False
        self.silent = False
        self.trace_id = None
        self.event_bindings = {}

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui is not None:
            self.editing = prev.editing
            self.variable = prev.variable
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if prev.trace_id:
                self.variable.trace_remove('write', prev.trace_id)
            for sequence, binding in prev.event_bindings.items():
                self.ui.unbind(sequence, binding)
            if not self.editing and self.curr_value.set(model_value):
                self.variable.set(model_value)
        else:
            self.variable = tk.StringVar(self.tkparent.inner, model_value)
            self.curr_value = Prop(model_value)
            self.ui = ttk.Entry(self.tkparent.inner, textvariable=self.variable,
                               show='*' if self._masked else '')
        self.trace_id = self.variable.trace_add('write', self.on_variable_changed)
        self.event_bindings = {
            '<Return>': self.ui.bind('<Return>', self.on_return),
            '<FocusOut>': self.ui.bind('<FocusOut>', self.on_focus_out),
        }
        if self.edit_model and not self.editing:
            self.edit_model.value = model_value
        super().update(prev)

    def on_variable_changed(self, *args):
        node = self.get_node()
        if node.destroyed or node.silent:
            return
        node.editing = True
        value = node.variable.get()
        if node.edit_model:
            node.edit_model.value = value
        event = PUIEvent()
        event.value = value
        node._input(event)

    def on_change(self):
        node = self.get_node()
        if node.destroyed or not node.editing:
            return
        node.editing = False
        value = node.variable.get()
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        model_value = str(node.model.value)
        node.silent = True
        try:
            node.variable.set(model_value)
        finally:
            node.silent = False
        node.curr_value.set(model_value)
        event = PUIEvent()
        event.value = value
        node._change(event)

    def on_return(self, event):
        self.on_change()
        self.get_node().tkparent.ui.focus_set()
        return 'break'

    def on_focus_out(self, event):
        self.on_change()

    def destroy(self, direct):
        if self.trace_id:
            try:
                self.variable.trace_remove('write', self.trace_id)
            except tk.TclError:
                pass
            self.trace_id = None
        super().destroy(direct)


class MaskedField(TextField):
    """Single-line password editor with TextField binding and event semantics."""
    _masked = True
