from __future__ import annotations
from .. import _typing as _t
from .base import *
from pathlib import Path


class Image(FBase):
    pui_terminal = True

    def __init__(self, path: _t.Any) -> None:
        super().__init__()
        self.path = path

    def update(self, prev):
        path = Path(self.path)
        key = (str(path), path.stat().st_mtime_ns)
        if prev and prev.ui is not None:
            self.ui, self.source_key = prev.ui, prev.source_key
        else:
            self.ui, self.source_key = ft.Image(src=b''), None
        if key != self.source_key:
            self.ui.src = path.read_bytes()
            self.source_key = key
        self.ui.fit = ft.BoxFit.CONTAIN
        self.ui.width, self.ui.height = self.layout_width, self.layout_height
        super().update(prev)
