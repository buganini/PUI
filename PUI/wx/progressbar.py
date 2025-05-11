from .. import *
from .base import *

class ProgressBar(WxBaseWidget):
    expand_x_prio = 1

    def __init__(self, progress, maximum=1):
        super().__init__()
        self.progress = progress
        self.maximum = maximum

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.Gauge(getWindow(self.parent))
        self.ui.SetRange(self.maximum)
        self.ui.SetValue(self.progress)
        super().update(prev)
