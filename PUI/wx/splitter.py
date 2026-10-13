from .base import *


def _reparent(content, parent):
    if isinstance(content, wx.Window):
        content.Reparent(parent)
    elif isinstance(content, wx.Sizer):
        for item in content.GetChildren():
            if item.IsWindow():
                item.GetWindow().Reparent(parent)
            elif item.IsSizer():
                _reparent(item.GetSizer(), parent)


class _Pane(wx.Panel):
    def mount(self, child):
        self.child = child
        _reparent(child.outer, self)
        outer, self.row, self.content, self.padding = WxBaseLayout.paddedChild(self, child)
        self.SetSizer(outer)
        self.apply()

    def unmount(self, parent):
        child = self.child.get_node()
        self.row.Detach(child.outer)
        self.SetSizer(None, deleteOld=True)
        _reparent(child.outer, parent)

    def apply(self):
        self.child = self.child.get_node()
        top, right, bottom, left = self.child.layout_padding or (0, 0, 0, 0)
        for item, size in zip(self.padding, ((0, top), (right, 0), (0, bottom), (left, 0))):
            item.SetMinSize(size)
        self.content.SetMinSize(self.child.wxMinSize())
        self.Layout()


class _SplitterHost(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.panes = []
        self.detached = {}
        self.splitters = []
        self.signature = None

    def add(self, idx, child):
        pane = self.detached.pop(child.outer, None)
        if pane is None:
            pane = _Pane(self)
        pane.mount(child)
        self.panes.insert(idx, pane)

    def remove(self, idx, child):
        pane = self.panes.pop(idx)
        pane.unmount(self)
        pane.Hide()
        self.detached[child.outer] = pane

    def reconcile(self, vertical):
        for pane in self.panes:
            pane.apply()
        signature = (vertical, tuple(self.panes))
        if signature == self.signature:
            return

        # Detach pane panels before deleting old native splitters. Their controls
        # and sizers remain alive, including during keyed moves.
        self.GetSizer().Clear()
        for splitter in self.splitters:
            if splitter.IsSplit():
                splitter.Unsplit()
        for pane in self.panes + list(self.detached.values()):
            pane.Reparent(self)
        for splitter in self.splitters:
            splitter.Reparent(self)
        for splitter in self.splitters:
            splitter.Destroy()
        self.splitters.clear()
        for pane in self.detached.values():
            pane.Destroy()
        self.detached.clear()

        if self.panes:
            tail = self.panes[-1]
            tail.Show()
            for idx in range(len(self.panes) - 2, -1, -1):
                splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
                splitter.SetMinimumPaneSize(1)  # Keep declared panes attached.
                remaining = len(self.panes) - idx
                splitter.SetSashGravity(1 / remaining)
                first = self.panes[idx]
                first.Reparent(splitter)
                tail.Reparent(splitter)
                split = splitter.SplitHorizontally if vertical else splitter.SplitVertically
                split(first, tail)
                self.splitters.insert(0, splitter)
                tail = splitter
            self.GetSizer().Add(tail, 1, wx.EXPAND)
            self.Layout()
            # Allocate equal initial space to each pane, accounting for all the
            # nested sashes. Gravity shares subsequent size changes the same way.
            for idx, splitter in enumerate(self.splitters):
                length = splitter.GetClientSize().height if vertical else splitter.GetClientSize().width
                remaining = len(self.panes) - idx
                usable = length - splitter.GetSashSize() * (remaining - 1)
                splitter.SetSashPosition(max(1, usable // remaining))
                splitter.UpdateSize()
        self.signature = signature


class Splitter(WxBaseWidget):
    """Multiple panes composed into native right/bottom-nested splitters."""
    pui_terminal = False
    expand_x_prio = 2
    expand_y_prio = 2

    def __init__(self, vertical=False):
        super().__init__()
        self.vertical = vertical

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui else _SplitterHost(getWindow(self.parent))
        super().update(prev)

    def addChild(self, idx, child):
        if not child.pui_outoforder:
            self.ui.add(idx, child)

    def removeChild(self, idx, child):
        if not child.pui_outoforder:
            self.ui.remove(idx, child)

    def postSync(self):
        self.ui.reconcile(self.vertical)
