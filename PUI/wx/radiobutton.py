from .. import *
from .base import *

class RadioButton(WxBaseWidget):
    def __init__(self, text, value, model):
        super().__init__()
        self.var = None
        self.text = text
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
        else:
            self.ui = wx.RadioButton(getWindow(self.parent), label=self.text, style=wx.RB_SINGLE)
            self.ui.Bind(wx.EVT_RADIOBUTTON, self._selected)

        self.ui.SetValue(self.model.value == self.value)

        super().update(prev)

    def _selected(self, *args, **kwargs):
        node = self.get_node()
        node.model.value = node.value
        node._clicked()