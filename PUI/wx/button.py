from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Button(WxBaseWidget):
    _internal_tag = 'native'

    def __init__(self, text: _t.Any, *, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.disabled = disabled

    def style(self: _t.NodeT, color: int | None = None,
              bgColor: int | None = None, fontSize: _t.Number | None = None,
              fontWeight: FontWeight | int | None = None,
              fontFamily: str | None = None) -> _t.NodeT:
        super().style(color, bgColor, fontSize, fontWeight, fontFamily)
        if wx.Platform == '__WXMAC__' and (self.style_color is not None or self.style_bgcolor is not None):
            # Cocoa buttons do not honour arbitrary text/background colours.
            # A different DOM key remounts the control when entering/leaving
            # custom painting, while ordinary buttons keep the native theme.
            self._internal_tag = 'coloured'
            self.genKey()
        return self

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
            self.ui.Unbind(wx.EVT_BUTTON)
        else:
            button_type = wx.Button
            if self._internal_tag == 'coloured':
                from wx.lib.buttons import GenButton
                button_type = GenButton
            self.ui = button_type(getWindow(self.parent), label=self.text, style=wx.BU_EXACTFIT)
        self.ui.Bind(wx.EVT_BUTTON, self._clicked)
        self.ui.Enable(not self.disabled)
        super().update(prev)
