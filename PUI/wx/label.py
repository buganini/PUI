from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

if wx.Platform == '__WXMAC__':
    # Cocoa StaticText accepts background colours but does not paint them.
    # Retain the generic control across colour changes and grid reflow.
    from wx.lib.stattext import GenStaticText

    class _StaticText(GenStaticText):
        def OnPaint(self, event):
            node = getattr(self, 'pui_node', None)
            if node is None or node.style_bgcolor is None:
                return super().OnPaint(event)
            # BG_STYLE_SYSTEM alone can leave compact Cocoa labels transparent.
            # Paint the requested background on every expose, not just resize.
            dc = wx.PaintDC(self)
            dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
            dc.Clear()
            dc.SetFont(self.GetFont())
            dc.SetTextForeground(self.GetForegroundColour() if self.IsEnabled()
                                 else wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            y = 0
            for line in self.GetLabel().split('\n'):
                dc.DrawText(line, 0, y)
                y += dc.GetTextExtent(line or 'W')[1]
else:
    _StaticText = wx.StaticText

class _StyledText(WxBaseWidget):
    def style(self: _t.NodeT, color: int | None = None,
              bgColor: int | None = None, fontSize: _t.Number | None = None,
              fontWeight: FontWeight | int | None = None,
              fontFamily: str | None = None) -> _t.NodeT:
        super().style(color, bgColor, fontSize, fontWeight, fontFamily)
        if wx.Platform == '__WXMAC__' and not self.selectable and self.style_bgcolor is not None:
            self._internal_tag = 'coloured'
            self.genKey()
        return self

    def static_text_type(self):
        return _StaticText if self._internal_tag == 'coloured' else wx.StaticText


class Label(_StyledText):
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
                self.ui = self.static_text_type()(getWindow(self.parent), label=self.text)
        self.ui.Bind(wx.EVT_LEFT_DOWN, self.on_click)

        super().update(prev)

    def on_click(self, event):
        self._clicked()
        event.Skip()
