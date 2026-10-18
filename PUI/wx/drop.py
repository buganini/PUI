"""wx composite drop target for file lists, Unicode text and URI lists."""
from pathlib import Path
import wx
from ..drop import DropEvent, DropFile, dispatch


class DropTarget(wx.DropTarget):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.files = wx.FileDataObject()
        self.text = wx.TextDataObject()
        self.uris = wx.CustomDataObject('text/uri-list')
        self.data = wx.DataObjectComposite()
        self.data.Add(self.files, True)
        self.data.Add(self.text)
        self.data.Add(self.uris)
        self.SetDataObject(self.data)

    def OnEnter(self, x, y, result):
        node = self.node.get_node()
        if node._onDragEntered:
            callback, args, kwargs = node._onDragEntered
            callback(DropEvent(x=x, y=y, action=self.action(result)), *args, **kwargs)
        return self.OnDragOver(x, y, result)

    def OnDragOver(self, x, y, result):
        node = self.node.get_node()
        return result if node._onDropped and not node.destroyed else wx.DragNone

    @staticmethod
    def action(result):
        return {wx.DragCopy: 'copy', wx.DragMove: 'move', wx.DragLink: 'link'}.get(result, 'copy')

    def OnData(self, x, y, result):
        if result not in (wx.DragCopy, wx.DragMove, wx.DragLink) or not self.GetData():
            return wx.DragNone
        fmt = self.data.GetReceivedFormat()
        files, text, urls = [], None, []
        if fmt == self.files.GetFormat():
            files = [DropFile(Path(p).name, p) for p in self.files.GetFilenames()]
        elif fmt == self.text.GetFormat():
            text = self.text.GetText()
        else:
            urls = [s for s in bytes(self.uris.GetData()).decode('utf-8').splitlines() if s and not s.startswith('#')]
        event = DropEvent(files=files, text=text, urls=urls, x=x, y=y, action=self.action(result))
        try:
            dispatch(self.node, event)
        except Exception:
            import logging
            logging.getLogger('PUI').exception('Drop handler failed')
            return wx.DragNone
        return result if event.accepted else wx.DragNone
