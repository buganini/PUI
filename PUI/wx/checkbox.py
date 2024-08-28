from .. import *
from .base import *

class Checkbox(WxBaseWidget):
    def __init__(self, text, model):
        super().__init__()
        self.text = text
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
        else:
            self.ui = wx.CheckBox(getWindow(self.parent), label=self.text)
            self.ui.Bind(wx.EVT_CHECKBOX, self._checked)

        self.ui.SetValue(self.model.value)

        super().update(prev)

    def _checked(self, *args, **kwargs):
        node = self.get_node()
        node.model.value = node.ui.GetValue()
        node._clicked()