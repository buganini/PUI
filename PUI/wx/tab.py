from __future__ import annotations
from .. import _typing as _t
from ..common import Side
from .base import *
from ..selection import TabsMixin


class Tabs(TabsMixin, WxBaseWidget):
    expand_x_prio = expand_y_prio = 3
    pui_terminal = False

    def __init__(self, tabposition: Side = Side.Top, model: _t.Binding[_t.Any] | None = None) -> None:
        if not isinstance(tabposition, Side):
            raise TypeError('tabposition must be a Side')
        self._internal_tag = tabposition
        super().__init__(model=model)
        self.tabposition = tabposition

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.pages = prev.pages
        else:
            style = {Side.Top: wx.NB_TOP, Side.Bottom: wx.NB_BOTTOM,
                     Side.Right: wx.NB_RIGHT, Side.Left: wx.NB_LEFT}[self.tabposition]
            self.ui = wx.Notebook(getWindow(self.parent), style=style)
            self.ui.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._tab_changed)
            self.pages = []
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        self.ui.InsertPage(idx, child.outer, child.label)
        self.pages.insert(idx, child)

    def removeChild(self, idx, child):
        self.ui.RemovePage(idx)  # Detach rather than destroy during keyed moves.
        self.pages.pop(idx)

    def postSync(self):
        for i, page in enumerate(self.pages):
            page = page.get_node()
            self.pages[i] = page
            self.ui.SetPageText(i, page.label)
        super().postSync()

    def _show_tab(self, index):
        if index is not None:
            self.ui.ChangeSelection(index)

    def _tab_changed(self, event):
        self._native_selected(event.GetSelection())
        event.Skip()


class Tab(WxSingleChild):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui else wx.Panel(getWindow(self.parent))
        super().update(prev)
