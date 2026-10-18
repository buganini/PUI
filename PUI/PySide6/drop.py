"""Adapt Qt's synchronous MIME events without exposing their lifetime to callbacks."""
from pathlib import Path
from PySide6 import QtCore
from ..drop import DropEvent, DropFile, dispatch


def event_data(event):
    mime = event.mimeData()
    urls = mime.urls() if mime.hasUrls() else []
    files = [DropFile(Path(u.toLocalFile()).name, u.toLocalFile()) for u in urls if u.isLocalFile()]
    actions = {QtCore.Qt.CopyAction: 'copy', QtCore.Qt.MoveAction: 'move', QtCore.Qt.LinkAction: 'link'}
    pos = event.position()
    return DropEvent(files=files, text=mime.text() if mime.hasText() else None,
                     urls=[u.toString() for u in urls if not u.isLocalFile()],
                     x=pos.x(), y=pos.y(), action=actions.get(event.proposedAction(), 'copy'))


def handle(node, event, *, entering=False):
    data = event_data(event)
    if entering:
        if node._onDragEntered:
            callback, args, kwargs = node._onDragEntered
            callback(data, *args, **kwargs)
        if node._onDropped:
            event.acceptProposedAction()
        else:
            event.ignore()
    else:
        event.ignore()
        dispatch(node, data)
        if data.accepted:
            event.acceptProposedAction()
        else:
            event.ignore()
    return True
