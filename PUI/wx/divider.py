from .. import *
from .base import *
from .layout import *

class Divider(WxBaseWidget):
    def __init__(self):
        super().__init__()

    def update(self, prev):
        vertical = bool(getattr(self.wxparent, 'container_x', False))
        self.expand_x_prio = 0 if vertical else 1
        self.expand_y_prio = 1 if vertical else 0
        style = wx.LI_VERTICAL if vertical else wx.LI_HORIZONTAL
        if prev and prev.ui:
            self.ui = prev.ui
            if self.ui.IsVertical() != vertical:
                flags = self.ui.GetWindowStyleFlag() & ~(wx.LI_HORIZONTAL | wx.LI_VERTICAL)
                self.ui.SetWindowStyleFlag(flags | style)
                self.ui.InvalidateBestSize()
        else:
            self.ui = wx.StaticLine(getWindow(self.parent), style=style)

        super().update(prev)
