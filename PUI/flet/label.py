from .base import *


class Label(FBase):
    pui_terminal = True

    def __init__(self, text, selectable=False):
        super().__init__()
        self.text, self.selectable = text, selectable

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Text()
        self.ui.value = self.text
        self.ui.selectable = self.selectable
        self.ui.on_tap = self._clicked if self._onClicked else None
        super().update(prev)
