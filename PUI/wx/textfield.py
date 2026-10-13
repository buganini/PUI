from .. import *
from .base import *

class TextField(WxBaseWidget):
    expand_x_prio = 3

    def __init__(self, model, edit_model=None, *, placeholder=None):
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder
        self.editing = False
        self.changed_cb = None

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if not self.editing and self.curr_value.set(model_value):
                self.ui.ChangeValue(model_value)
            self.ui.Unbind(wx.EVT_TEXT)
            self.ui.Unbind(wx.EVT_KILL_FOCUS)
            self.ui.Unbind(wx.EVT_TEXT_ENTER)
        else:
            self.curr_value = Prop(model_value)
            self.ui = wx.TextCtrl(getWindow(self.parent), style=wx.TE_PROCESS_ENTER)
            self.ui.ChangeValue(model_value)
        self.ui.Bind(wx.EVT_TEXT, self.on_textchanged)
        self.ui.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)
        self.ui.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        self.ui.SetHint('' if self.placeholder is None else self.placeholder)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_enter(self, event):
        node = self.get_node()
        node.commit()
        getWindow(node.parent).SetFocus()

    def on_textchanged(self, event):
        node = self.get_node()
        if node.destroyed or not node.ui:
            return
        node.editing = True
        value = node.ui.GetValue()
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        node._input(e)
        event.Skip()

    def commit(self):
        node = self.get_node()
        if not node.editing or node.destroyed or not node.ui:
            return
        node.editing = False
        value = node.ui.GetValue()
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        model_value = str(node.model.value)
        node.ui.ChangeValue(model_value)
        node.curr_value.set(model_value)
        e = PUIEvent()
        e.value = value
        node._change(e)

    def on_kill_focus(self, event):
        self.commit()
        event.Skip()
