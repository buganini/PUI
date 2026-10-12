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

    def applyChildren(self):
        for child, si in self.updateSizerItems():
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            si.SetFlag(wx.EXPAND)
            for item, size in zip(si.padding_items, ((0, top), (right, 0), (0, bottom), (left, 0))):
                item.SetMinSize(size)
            self.applyChildLayoutSize(child, si.content_item)

    def addChild(self, idx, child):
        if isinstance(child, (WxBaseLayout, WxBaseWidget)):
            outer, row, content, padding = self.paddedChild(child)
            si = self.ui.Add(outer, pos=(child.grid_row, child.grid_column),
                             span=(child.grid_rowspan or 1, child.grid_columnspan or 1),
                             flag=wx.EXPAND)
            si.content_row = row
            si.content_item = content
            si.padding_items = padding
            self.sizerItems.insert(idx, (child, si))
            self.relayout = True
