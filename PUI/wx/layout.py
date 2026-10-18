from .. import *
from .base import *

class HBox(WxBaseLayout):
    container_x = True
    expand_x_prio = 2
    expand_y_prio = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.HORIZONTAL)
        super().update(prev)

class VBox(WxBaseLayout):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 2

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.VERTICAL)
        super().update(prev)

class Spacer(WXBase):
    pui_terminal = True
    def __init__(self):
        super().__init__()
        self.layout_weight = 1

class Grid(WxBaseLayout):
    pui_grid_layout = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.GridBagSizer()
        super().update(prev)

    def applyChildren(self):
        for child, si in self.updateSizerItems():
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            si.SetFlag(wx.EXPAND)
            for item, size in zip(si.padding_items, ((0, top), (right, 0), (0, bottom), (left, 0))):
                item.SetMinSize(size)
            self.applyChildLayoutSize(child, si.content_item)

    def addChild(self, idx, child):
        if isinstance(child, (WxBaseLayout, WxBaseWidget)):
            outer, row, content, padding = self.paddedChild(child)
            si = self.ui.Add(outer, pos=(child.grid_row, child.grid_column),
                             span=(child.grid_rowspan or 1, child.grid_columnspan or 1),
                             flag=wx.EXPAND)
            si.content_row = row
            si.content_item = content
            si.padding_items = padding
            self.sizerItems.insert(idx, (child, si))
            self.relayout = True


class _OverlaySizer(wx.Sizer):
    def CalcMin(self):
        sizes = [item.CalcMin() for item in self.GetChildren()]
        return wx.Size(max((s.width for s in sizes), default=0),
                       max((s.height for s in sizes), default=0))

    def RepositionChildren(self, minSize):
        for item in self.GetChildren():
            item.SetDimension(self.GetPosition(), self.GetSize())


class Stack(WxBaseWidget):
    """Native panel whose child sizers share the same rectangle."""
    pui_terminal = False
    expand_x_prio = 2
    expand_y_prio = 2

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.sizerItems = prev.sizerItems
        else:
            self.ui = wx.Panel(getWindow(self.parent))
            self.ui.SetSizer(_OverlaySizer())
            self.sizerItems = []
        super().update(prev)

    def addChild(self, idx, child):
        if child.pui_outoforder:
            return
        if isinstance(child, Spacer):
            item = self.ui.GetSizer().Insert(idx, (0, 0))
        else:
            outer, row, content, padding = WxBaseLayout.paddedChild(self, child)
            item = self.ui.GetSizer().Insert(idx, outer)
            item.content_row, item.content_item, item.padding_items = row, content, padding
        self.sizerItems.insert(idx, (child, item))

    def removeChild(self, idx, child):
        if child.pui_outoforder:
            return
        _, item = self.sizerItems.pop(idx)
        if hasattr(item, 'content_row'):
            item.content_row.Detach(child.outer)
        self.ui.GetSizer().Remove(idx)

    def postSync(self):
        def raise_windows(sizer):
            for item in sizer.GetChildren():
                if item.IsWindow():
                    item.GetWindow().Raise()
                elif item.IsSizer():
                    raise_windows(item.GetSizer())

        for child, item in WxBaseLayout.updateSizerItems(self):
            if hasattr(item, 'padding_items'):
                top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
                for pad, size in zip(item.padding_items, ((0, top), (right, 0), (0, bottom), (left, 0))):
                    pad.SetMinSize(size)
                item.content_item.SetMinSize(child.wxMinSize())
        self.ui.InvalidateBestSize()
        self.ui.Layout()
        raise_windows(self.ui.GetSizer())
        parent = self.wxparent
        if parent is not None and parent.ui:
            parent.ui.Layout()
        super().postSync()
