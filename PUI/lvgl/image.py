from __future__ import annotations
import os
from pathlib import Path
from .. import _typing as _t
from .base import *


class Image(LBaseWidget):
    """Image file decoded by LVGL (PNG/JPEG), scaled to the declared size."""

    def __init__(self, path: _t.Any) -> None:
        super().__init__()
        self.path = str(Path(path))

    def create(self, parent):
        return lib.lv_image_create(parent)

    def configure(self, prev):
        obj = self.ui
        store = self._native.store
        stamp = (self.path, os.path.getmtime(self.path) if os.path.exists(self.path) else None)
        if store.get('src') != stamp:
            lib.lv_image_set_src(obj, ('A:' + self.path).encode())
            store['src'] = stamp
        lib.lv_image_set_inner_align(obj, lib.LV_IMAGE_ALIGN_STRETCH if self.layout_weight else lib.LV_IMAGE_ALIGN_CONTAIN)
        lib.lv_image_set_antialias(obj, True)

    def _apply_dim(self, horizontal):
        w = lib.lv_image_get_src_width(self.ui)
        h = lib.lv_image_get_src_height(self.ui)
        width, height = self.layout_width, self.layout_height
        if w > 0 and h > 0:
            # Keep the aspect ratio when only one dimension is declared.
            if width is not None and height is None:
                height = round(h * width / w)
            elif height is not None and width is None:
                width = round(w * height / h)
            elif width is None:
                width, height = w, h
        self._set_dim(horizontal, (width if horizontal else height) or 'content')
        self._native.box_dims.discard('w' if horizontal else 'h')
