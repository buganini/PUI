from __future__ import annotations
from .. import _typing as _t
from .base import *


class Label(LBaseWidget):
    _default_size = ('content', 'content')

    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text = str(text)
        self._tag = self.text
        self.selectable = selectable

    def create(self, parent):
        return lib.lv_label_create(parent)

    def configure(self, prev):
        # Constrained widths wrap; otherwise the label keeps its natural size.
        wrap = self.layout_width is not None
        lib.lv_label_set_long_mode(self.ui, lib.LV_LABEL_LONG_MODE_WRAP if wrap else lib.LV_LABEL_LONG_MODE_CLIP)
        if prev is None or prev.text != self.text:
            lib.lv_label_set_text(self.ui, text_bytes(self.text))
