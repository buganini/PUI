from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Text(FBase):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text = text
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
        else:
            self.ui = ft.Text(self.text, expand=self.layout_weight)
        self.ui.selectable = self.selectable
        self.ui.expand = self.layout_weight
        super().update(prev)

class Html(FBase):
    pui_supported = False
    def __init__(self, text, selectable=False, *, openURL=True):
        super().__init__()
        self.text = text
        self.openURL = bool(openURL)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
        else:
            self.ui = ft.Text(self.text, expand=self.layout_weight)
        super().update(prev)

class MarkDown(FBase):
    pui_supported = True
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
        else:
            self.ui = ft.Markdown(self.text, expand=self.layout_weight, auto_follow_links=True)
        super().update(prev)
