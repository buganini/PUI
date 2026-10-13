from .base import *
from .layout import VBox
from ..views import ViewsMixin


class _Page(WxSingleChild):
    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui else wx.Panel(getWindow(self.parent))
        super().update(prev)


class Views(ViewsMixin, WxBaseWidget):
    expand_x_prio = 2
    expand_y_prio = 2

    def _page(self):
        return _Page().layout(padding=0)

    def _page_content(self, page):
        return VBox().layout(padding=0)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.Simplebook(getWindow(self.parent))
            self.ui.AddPage(wx.Panel(self.ui), '')
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.InsertPage(idx + 1, child.outer, '')

    def removeChild(self, idx, child):
        self.ui.RemovePage(idx + 1)

    def _show_view(self, index):
        self.ui.ChangeSelection(0 if index is None else index + 1)
