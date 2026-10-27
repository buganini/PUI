from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class Button(TBase):
    def __init__(self, text: _t.Any, *, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            if self.text != prev.text:
                self.ui.label = self.text
                self.ui.refresh(layout=True)
        else:
            self.ui = widgets.Button(self.text)
        self.ui.puinode = self
        self.ui.disabled = self.disabled
        super().update(prev)

    def t_update_layout(self):
        super().t_update_layout()
        if self.ui is not None:
            # None restores Textual's native 16-cell minimum. Keep buttons
            # content-sized unless PUI supplies a desired or minimum width.
            minimum = self._minimum_size('x')
            self.ui.styles.min_width = 0 if minimum is None else minimum
