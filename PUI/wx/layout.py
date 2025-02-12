from .. import *
from .base import *

class HBox(WxBaseLayout):
    container_x = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.HORIZONTAL)
        super().update(prev)

class VBox(WxBaseLayout):
    container_y = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.VERTICAL)
        super().update(prev)

class Spacer(WXBase):
    pui_terminal = True
    def __init__(self):
        super().__init__()
        self.layout_weight = 1

class Grid(WxBaseLayout):
    pui_grid_layout = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.GridBagSizer()
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, WxBaseLayout) or isinstance(child, WxBaseWidget):
            p = 0
            if child.layout_padding:
                p = max(child.layout_padding)
            self.ui.Add(child.outer, pos=(child.grid_row, child.grid_column), span=(child.grid_rowspan or 1, child.grid_columnspan or 1), flag=wx.ALL|wx.EXPAND, border=p)

    def removeChild(self, idx, child):
        if isinstance(child, WxBaseLayout) or isinstance(child, WxBaseWidget):
            pass
