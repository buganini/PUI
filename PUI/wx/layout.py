from .. import *
from .base import *

class HBox(WxBaseLayout):
    container_x = True
    expand_x_prio = 2
    expand_y_prio = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.HORIZONTAL)
        super().update(prev)

class VBox(WxBaseLayout):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 2

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

    def postUpdate(self):
        WXBase.postUpdate(self)

        for child, si in self.updateSizerItems():
            p = 0
            if child.layout_padding:
                p = max(child.layout_padding)
            si.SetFlag(wx.ALL | wx.EXPAND)
            si.SetBorder(p)
            self.applyChildLayoutSize(child, si)

    def addChild(self, idx, child):
        self.relayout = True
        if isinstance(child, WxBaseLayout) or isinstance(child, WxBaseWidget):
            p = 0
            if child.layout_padding:
                p = max(child.layout_padding)
            si = self.ui.Add(child.outer, pos=(child.grid_row, child.grid_column), span=(child.grid_rowspan or 1, child.grid_columnspan or 1), flag=wx.ALL|wx.EXPAND, border=p)
            self.sizerItems.insert(idx, (child, si))

    def removeChild(self, idx, child):
        self.relayout = True
        if isinstance(child, WxBaseLayout) or isinstance(child, WxBaseWidget):
            self.ui.Detach(child.outer)
            self.sizerItems.pop(idx)
