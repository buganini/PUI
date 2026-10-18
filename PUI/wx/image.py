from __future__ import annotations
from .. import _typing as _t
from .base import *
from pathlib import Path


class Image(WxBaseWidget):
    def __init__(self, path: _t.Any) -> None:
        super().__init__()
        self.path = path

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.source = prev.source
            self.source_key = prev.source_key
            self.ui.Unbind(wx.EVT_LEFT_DOWN)
        else:
            self.ui = wx.StaticBitmap(getWindow(self.parent))
            self.source_key = None
        path = Path(self.path)
        key = (str(path), path.stat().st_mtime_ns)
        if key != self.source_key:
            self.source = wx.Image(str(path))
            if not self.source.IsOk():
                raise ValueError(f'Cannot load image: {path}')
            self.source_key = key
        image = self.source
        width, height = self.layout_width, self.layout_height
        if width is not None or height is not None:
            scale = min(width / image.GetWidth() if width is not None else float('inf'),
                        height / image.GetHeight() if height is not None else float('inf'))
            image = image.Scale(max(1, int(image.GetWidth() * scale)),
                                max(1, int(image.GetHeight() * scale)), wx.IMAGE_QUALITY_HIGH)
        self.ui.SetBitmap(wx.Bitmap(image))
        self.ui.Bind(wx.EVT_LEFT_DOWN, self._clicked)
        super().update(prev)
