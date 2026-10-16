from .. import *
from .base import *

class RadioButton(WxBaseWidget):
    def __init__(self, text, value, model, *, disabled=False):
        super().__init__()
        self.var = None
        self.text = text
        self.disabled = disabled
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
            self.ui.Unbind(wx.EVT_RADIOBUTTON)
        else:
            self.ui = wx.RadioButton(getWindow(self.parent), label=self.text, style=wx.RB_SINGLE)
        self.ui.Bind(wx.EVT_RADIOBUTTON, self._selected)

        self.ui.SetValue(self.model.value == self.value)

        self.ui.Enable(not self.disabled)
        super().update(prev)

    def _selected(self, *args, **kwargs):
        node = self.get_node()
        node.model.value = node.value
        node._clicked()