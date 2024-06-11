from .. import *
from .base import *

class HBox(WxBaseLayout):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.HORIZONTAL)
        super().update(prev)

class VBox(WxBaseLayout):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.VERTICAL)
        super().update(prev)

class Spacer(PUINode):
    def __init__(self):
        super().__init__()
        self.layout_weight = 1

class Grid(WxBaseLayout):
    grid_layout = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.GridBagSizer()
            print(self.ui)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, WxBaseLayout) or isinstance(child, WxBaseWidget):
            self.ui.Add(child.outer, pos=(child.grid_row, child.grid_column), span=(child.grid_rowspan or 1, child.grid_columnspan or 1), flag=wx.ALL)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, WxBaseLayout) or isinstance(child, WxBaseWidget):
            pass
        elif child.children:
            self.removeChild(idx, child.children[0])
