from .. import *
from .base import *

class Button(WxBaseWidget):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
        else:
            self.ui = wx.Button(getWindow(self.parent), label=self.text)
            self.ui.Bind(wx.EVT_BUTTON, self._clicked)
        super().update(prev)
