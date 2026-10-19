import wx
from .base import getWindow


def observe(node):
    ui = node.ui
    host = ui if isinstance(ui, wx.Window) else getWindow(node.parent)
    pending = False
    closed = False

    def measure():
        nonlocal pending
        pending = False
        if closed or node.get_node().destroyed or not host:
            return
        if isinstance(ui, wx.Sizer):
            size = ui.GetSize()
        else:
            size = ui.GetClientSize()
        node._set_size(size.width, size.height)

    def schedule(event=None):
        nonlocal pending
        if event is not None:
            event.Skip()
        if not pending:
            pending = True
            wx.CallAfter(measure)

    host.Bind(wx.EVT_SIZE, schedule)
    node._size_refresh = schedule
    schedule()
    def close():
        nonlocal closed
        closed = True
        if host:
            host.Unbind(wx.EVT_SIZE, handler=schedule)
    return close
