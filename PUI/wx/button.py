from .. import *
from .base import *

class Button(WxBaseWidget):
    def __init__(self, text, *, disabled=False):
        super().__init__()
        self.text = text
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
            self.ui.Unbind(wx.EVT_BUTTON)
        else:
            self.ui = wx.Button(getWindow(self.parent), label=self.text)
        self.ui.Bind(wx.EVT_BUTTON, self._clicked)
        self.ui.Enable(not self.disabled)
        super().update(prev)
