from .base import *


class Button(FBase):
    pui_terminal = True

    def __init__(self, text, *, enabled=True):
        super().__init__()
        self.text = text
        self.enabled = enabled

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Button()
        self.ui.content = self.text
        self.ui.on_click = self._clicked
        super().update(prev)
        self.ui.disabled = self.flet_params.get('disabled', not self.enabled)
