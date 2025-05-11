from .. import *
from .base import *

class TextField(WxBaseWidget):
    def __init__(self, model, edit_model=None):
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.editing = False
        self.changed_cb = None
        self.layout_width = 50
        self.layout_height = -1

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if self.curr_value.set(model_value) and not self.editing:
                self.ui.SetValue(model_value)
        else:
            self.curr_value = Prop(model_value)
            self.ui = wx.TextCtrl(getWindow(self.parent), style=wx.TE_PROCESS_ENTER)
            self.ui.SetValue(model_value)
            self.ui.Bind(wx.EVT_TEXT, self.on_textchanged)
            self.ui.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)
            self.ui.Bind(wx.EVT_TEXT_ENTER, self.on_enter)

        self.ui.SetMinSize((self.layout_width, self.layout_height))

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_enter(self, event):
        from .window import Window
        p = self.parent
        while p:
            if isinstance(p, Window):
                p.panel.SetFocus()
                break
            p = p.parent
        event.Skip()

    def on_textchanged(self, event): # editing
        node = self.get_node()
        node.editing = True
        value = self.ui.GetValue()
        if node.edit_model:
           node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)

    def on_kill_focus(self, event): # finish editing
        node = self.get_node()
        node.editing = False
        value = self.ui.GetValue()
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        self._change(e)
