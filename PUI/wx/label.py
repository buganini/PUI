from .. import *
from .base import *

class Label(WxBaseWidget):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = text
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
        else:
            self.ui = wx.StaticText(getWindow(self.parent), label=self.text)
            self.ui.Bind(wx.EVT_LEFT_DOWN, self._clicked)

        super().update(prev)
