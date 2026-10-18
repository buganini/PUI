from __future__ import annotations
from .. import _typing as _t
from .base import *


class Label(FBase):
    pui_terminal = True

    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text, self.selectable = text, selectable

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Text()
        self.ui.value = self.text
        self.ui.selectable = self.selectable
        self.ui.on_tap = self._clicked if self._onClicked else None
        super().update(prev)
        # Text.on_tap only fires for selectable text in Flet.
        self.shell.on_click = (
            self._clicked if self._onClicked and not self.ui.selectable else None
        )
