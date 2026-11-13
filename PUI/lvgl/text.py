from __future__ import annotations
from .. import _typing as _t
from .base import *


class Text(LBaseWidget):
    """Plain multi-line text, wrapped to the available width."""
    _default_size = (('pct', 100), 'content')

    def __init__(self, text: _t.Any = '', selectable: bool = False) -> None:
        super().__init__()
        self.text = str(text)
        self.selectable = selectable

    def create(self, parent):
        obj = lib.lv_label_create(parent)
        lib.lv_label_set_long_mode(obj, lib.LV_LABEL_LONG_MODE_WRAP)
        return obj

    def configure(self, prev):
        if prev is None or prev.text != self.text:
            lib.lv_label_set_text(self.ui, text_bytes(self.text))


class Html(Text):
    """No HTML renderer on LVGL; the markup is shown as plain text."""
    pui_supported = False

    def __init__(self, text, selectable=False, *, openURL=True):
        super().__init__(text, selectable)


class MarkDown(Text):
    """No Markdown renderer on LVGL; the source is shown as plain text."""
    pui_supported = False


Markdown = MarkDown
