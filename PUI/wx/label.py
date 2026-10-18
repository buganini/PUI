from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Label(WxBaseWidget):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        self._internal_tag = str(bool(selectable))
        super().__init__()
        self.text = text
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.ChangeValue(self.text) if self.selectable else self.ui.SetLabel(self.text)
            self.ui.Unbind(wx.EVT_LEFT_DOWN)
        else:
            if self.selectable:
                style = wx.TE_READONLY | wx.BORDER_NONE
                self.ui = wx.TextCtrl(getWindow(self.parent), value=self.text,
                                      style=style)
            else:
                self.ui = wx.StaticText(getWindow(self.parent), label=self.text)
        self.ui.Bind(wx.EVT_LEFT_DOWN, self.on_click)

        super().update(prev)

    def on_click(self, event):
        self._clicked()
        event.Skip()
