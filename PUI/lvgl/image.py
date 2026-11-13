from __future__ import annotations
from .. import _typing as _t
from .base import *
from pathlib import Path


class Image(LBaseWidget):
    def __init__(self, path: _t.Any) -> None:
        super().__init__()
        self.path = path

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = lib.pui_lv_image_create(self.lv_parent_obj)
            lib.pui_lv_obj_set_clickable(self.ui, 1)
        path = Path(self.path)
        lib.pui_lv_image_set_src_file(self.ui, str(path).encode())
        if self.layout_width is not None:
            lib.pui_lv_obj_set_width(self.ui, self.layout_width)
        if self.layout_height is not None:
            lib.pui_lv_obj_set_height(self.ui, self.layout_height)
        super().update(prev)
