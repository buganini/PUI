from .. import *
from .base import *

class Checkbox(WxBaseWidget):
    def __init__(self, text, model, value=None):
        super().__init__()
        self.text = text
        self.model = model
        self.value = text if value is None else value

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
        else:
            self.ui = wx.CheckBox(getWindow(self.parent), label=self.text)
            self.ui.Bind(wx.EVT_CHECKBOX, self._checked)

        self.ui.SetValue(checkbox_get(self.model, self.value))

        super().update(prev)

    def _checked(self, *args, **kwargs):
        node = self.get_node()
        checkbox_set(node.model, node.ui.GetValue(), self.value)
        node._clicked()