from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Text(TBase):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.update(self.text)
        else:
            self.ui = widgets.Label(self.text, markup=False)
        super().update(prev)

class Html(Text):
    pui_supported = False

    def __init__(self, text, selectable=False, *, openURL=True):
        super().__init__(text, selectable)
        self.openURL = bool(openURL)

class MarkDown(TBase):
    weak_expand_x = True
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.update(self.text)
        else:
            self.ui = widgets.Markdown(self.text)
        super().update(prev)
