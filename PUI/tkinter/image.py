from __future__ import annotations
from .. import _typing as _t
from .base import *
from pathlib import Path

try:
    from PIL import Image as PILImage, ImageTk
    _has_pil = True
except ImportError:
    _has_pil = False


class Image(TkBaseWidget):
    def __init__(self, path: _t.Any) -> None:
        super().__init__()
        self.path = path

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.source_key = prev.source_key
            self._photo = prev._photo
        else:
            self.ui = tk.Label(self.tkparent.inner)
            self.ui.bind("<Button-1>", self._clicked)
            self.source_key = None
            self._photo = None

        if self._onClicked:
            self.ui.config(cursor="hand2")

        path = Path(self.path)
        key = (str(path), path.stat().st_mtime_ns,
               self.layout_width, self.layout_height)
        if key != self.source_key:
            width, height = self.layout_width, self.layout_height
            if _has_pil:
                img = PILImage.open(path)
                if width is not None or height is not None:
                    scale = min(width / img.width if width is not None else float('inf'),
                                height / img.height if height is not None else float('inf'))
                    img = img.resize((max(1, int(img.width * scale)),
                                      max(1, int(img.height * scale))),
                                     PILImage.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
            else:
                photo = tk.PhotoImage(file=str(path))
                if width is not None or height is not None:
                    pw, ph = photo.width(), photo.height()
                    if pw > 0 and ph > 0:
                        scale = min(width / pw if width is not None else float('inf'),
                                    height / ph if height is not None else float('inf'))
                        if scale >= 1:
                            factor = max(1, round(scale))
                            photo = photo.zoom(factor, factor)
                        else:
                            factor = max(1, round(1 / scale))
                            photo = photo.subsample(factor, factor)
                self._photo = photo
            self.ui.config(image=self._photo)
            self.source_key = key

        super().update(prev)
