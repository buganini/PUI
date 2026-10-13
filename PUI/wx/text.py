from .. import *
from .base import *
import wx.html


class _HtmlWindow(wx.html.HtmlWindow):
    def DoGetBestClientSize(self):
        content = self.GetInternalRepresentation()
        if content is None:
            return super().DoGetBestClientSize()
        return wx.Size(content.GetWidth(), content.GetHeight())

class Text(WxBaseWidget):
    def __init__(self, text, selectable=False):
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
                self.ui = wx.StaticText(getWindow(self.parent), label=self.text)

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
        self.ui.SetPage(self.text)
        self.ui.InvalidateBestSize()
        super().update(prev)

class MarkDown(Text):
    pui_supported = False
