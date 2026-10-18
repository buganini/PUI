from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class ProgressBar(WxBaseWidget):
    expand_x_prio = 1

    def __init__(self, progress: _t.Number, maximum: _t.Number = 1) -> None:
        super().__init__()
        self.progress = progress
        self.maximum = maximum

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.Gauge(getWindow(self.parent))
        self.ui.SetRange(max(1, int(self.maximum * 100)))
        self.ui.SetValue(max(0, min(self.ui.GetRange(), int(self.progress * 100))))
        super().update(prev)
