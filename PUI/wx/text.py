from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
from .label import _StyledText
import wx.html


class _HtmlWindow(wx.html.HtmlWindow):
    def DoGetBestClientSize(self):
        content = self.GetInternalRepresentation()
        if content is None:
            return super().DoGetBestClientSize()
        return wx.Size(content.GetWidth(), content.GetHeight())

class Text(_StyledText):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        self._internal_tag = str(bool(selectable))
        super().__init__()
        self.text = text
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.ChangeValue(self.text) if self.selectable else self.ui.SetLabel(self.text)
        else:
            if self.selectable:
                style = wx.TE_READONLY | wx.BORDER_NONE
                self.ui = wx.TextCtrl(getWindow(self.parent), value=self.text,
                                      style=style | wx.TE_MULTILINE)
            else:
                self.ui = self.static_text_type()(getWindow(self.parent), label=self.text)

        super().update(prev)

class Html(WxBaseWidget):
    expand_x_prio = 3
    expand_y_prio = 3

    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = text
        self.selectable = selectable

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui else _HtmlWindow(getWindow(self.parent))
        super().update(prev)
        # HtmlWindow's parser starts with the system text colour, regardless
        # of SetForegroundColour. Supply a default without replacing explicit
        # colours in the HTML (including the cookbook syntax highlighting).
        source = self.text
        if self.style_color is not None:
            source = f'<font color="#{self.style_color:06x}">{source}</font>'
        self.ui.SetPage(source)
        # SetPage resets the native background while parsing the document.
        if self.style_bgcolor is not None:
            self.ui.SetBackgroundColour(int_to_wx_colour(self.style_bgcolor))
        self.ui.InvalidateBestSize()

class MarkDown(Text):
    pui_supported = False
