from ..grid import GridMixin, native_stretches
from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *

class HBox(_BoxMixin, WxBaseLayout):
    container_x = True
    expand_x_prio = 3
    expand_y_prio = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = wx.BoxSizer(wx.HORIZONTAL)
        super().update(prev)

class VBox(_BoxMixin, WxBaseLayout):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 3

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

class Grid(GridMixin, WxBaseLayout):
    pui_grid_layout = True
    expand_x_prio = expand_y_prio = 1
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.mounted = prev.mounted
            self.growable = prev.growable
            self.growable_rows = prev.growable_rows
        else:
            self.ui = wx.GridBagSizer()
            self.mounted, self.growable = [], set()
            self.growable_rows = set()
        super().update(prev)

    def applyChildren(self):
        for child, si in self.updateSizerItems():
            show_item(child, si)
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            si.SetFlag(wx.EXPAND)
            for item, size in zip(si.padding_items, ((0, top), (right, 0), (0, bottom), (left, 0))):
                item.SetMinSize(size)
            self.applyChildLayoutSize(child, si.content_item)

    def _detach(self):
        for child, item in self.sizerItems:
            if hasattr(item, 'content_row'):
                item.content_row.Detach(child.get_node().outer)
        self.ui.Clear(delete_windows=False)
        self.sizerItems = []

    def preSync(self):
        self._detach()
        super().preSync()

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)

    def postSync(self):
        self._detach()
        cells = self.grid_cells(self.mounted)
        columns, rows = self.grid_stretches(cells)
        columns, rows = native_stretches(columns), native_stretches(rows)
        for column in self.growable:
            self.ui.RemoveGrowableCol(column)
        for row in self.growable_rows:
            self.ui.RemoveGrowableRow(row)
        self.growable = {i for i, weight in enumerate(columns) if weight}
        self.growable_rows = {i for i, weight in enumerate(rows) if weight}
        for child in self.mounted:
            child = child.get_node()
            if not child._visible:
                if isinstance(child.ui, wx.Window):
                    child.ui.Hide()
                elif isinstance(child.ui, wx.Sizer):
                    child.ui.ShowItems(False)
        for child, (row, column, rowspan, columnspan) in cells:
            outer, content_row, content, padding = self.paddedChild(child)
            item = self.ui.Add(outer, pos=(row, column), span=(rowspan, columnspan), flag=wx.EXPAND)
            item.content_row, item.content_item, item.padding_items = content_row, content, padding
            self.sizerItems.append((child, item))
        for column in self.growable:
            self.ui.AddGrowableCol(column, int(columns[column]))
        for row in self.growable_rows:
            self.ui.AddGrowableRow(row, int(rows[row]))
        super().postSync()


class _OverlaySizer(wx.Sizer):
    def CalcMin(self):
        sizes = [item.CalcMin() for item in self.GetChildren() if item.IsShown()]
        return wx.Size(max((s.width for s in sizes), default=0),
                       max((s.height for s in sizes), default=0))

    def RepositionChildren(self, minSize):
        for item in self.GetChildren():
            item.SetDimension(self.GetPosition(), self.GetSize())


class Stack(WxBaseWidget):
    """Native panel whose child sizers share the same rectangle."""
    pui_terminal = False
    expand_x_prio = 3
    expand_y_prio = 3

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
                    window = item.GetWindow()
                    if wx.Platform == '__WXMSW__':
                        # Lower siblings must not repaint over raised layers.
                        window.SetWindowStyleFlag(window.GetWindowStyleFlag() | wx.CLIP_SIBLINGS)
                    window.Raise()
                elif item.IsSizer():
                    raise_windows(item.GetSizer())

        for child, item in WxBaseLayout.updateSizerItems(self):
            show_item(child, item)
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


class _AdaptiveLayout(HBox):
    def update(self, prev):
        super().update(prev)
        self.ui.SetOrientation(wx.HORIZONTAL if self.container_x else wx.VERTICAL)


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
