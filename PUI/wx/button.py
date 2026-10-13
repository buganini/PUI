from .. import *
from .base import *

class Button(WxBaseWidget):
    def __init__(self, text, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
            self.ui.Unbind(wx.EVT_BUTTON)
        else:
            self.ui = wx.Button(getWindow(self.parent), label=self.text)
        self.ui.Bind(wx.EVT_BUTTON, self._clicked)
        self.ui.Enable(self.enabled)
        super().update(prev)
