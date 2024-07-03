from .. import *
from .base import *

class TextField(WxBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.editing = False
        self.changed_cb = None

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if self.curr_value.set(model_value):
                self.ui.SetValue(model_value)
        else:
            self.curr_value = Prop(model_value)
            self.ui = wx.TextCtrl(getWindow(self.parent))
            self.ui.SetValue(model_value)
            self.ui.Bind(wx.EVT_TEXT, self.on_textchanged)
        super().update(prev)

    def change(self, cb, *args, **kwargs):
        self.changed_cb = (cb, args, kwargs)

    def on_textchanged(self, *args):
        node = self.get_node()
        node.editing = True
        node.model.value = self.ui.GetValue()
        if node.changed_cb:
            node.changed_cb[0](*node.changed_cb[1], **node.changed_cb[2])
