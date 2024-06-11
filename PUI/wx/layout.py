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
            self.layout = prev.layout
        else:
            self.ui = wx.BoxSizer(wx.VERTICAL)
        super().update(prev)

class Spacer(PUINode):
    def __init__(self):
        super().__init__()
        self.layout_weight = 1
