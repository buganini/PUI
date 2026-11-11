from __future__ import annotations
from dataclasses import field, replace
from .. import _typing as _t
from .base import *


@ft.value
class _ContentButtonStyle(ft.ButtonStyle):
    # Flet 1.0.4's Flutter client reads minimum_size, but the Python ButtonStyle
    # omits it. Keep the field when Flet copies the style before serialization.
    minimum_size: ft.Size = field(default_factory=lambda: ft.Size(0, 0))

    def copy(self, **kwargs):
        return replace(self, **{key: value for key, value in kwargs.items() if value is not None})


class Button(FBase):
    pui_terminal = True

    def __init__(self, text: _t.Any = '', *, icon: _t.Any = None, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.icon = icon
        self.disabled = disabled

    def apply_style(self):
        super().apply_style()
        self.ui.style = _ContentButtonStyle(text_style=self.ui.style.text_style)

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Button()
        self.ui.content = self.text if self.text else None
        if self.icon is not None:
            self.ui.icon = str(self.icon)
        else:
            self.ui.icon = None
        self.ui.on_click = self._clicked
        super().update(prev)
        self.ui.disabled = self.flet_params.get('disabled', self.disabled)
