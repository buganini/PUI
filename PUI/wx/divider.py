from .. import *
from .base import *
from .layout import *

class Divider(WxBaseWidget):
    def __init__(self):
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            if isinstance(self.non_virtual_parent, VBox):
                style = wx.LI_HORIZONTAL
            else:
                style = wx.LI_VERTICAL
            self.ui = wx.StaticLine(getWindow(self.parent), style=style, size=(15, 15))

        super().update(prev)
