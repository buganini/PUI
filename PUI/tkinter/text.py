from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Text(TkBaseWidget):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.config(text = self.text)
        else:
            self.ui = tk.Label(self.tkparent.inner, text=self.text, anchor="w", justify="left")
        super().update(prev)

class Html(Text):
    pui_supported = False

class MarkDown(Text):
    pui_supported = False
