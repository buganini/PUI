from .. import *
from .base import *

class FElevatedButton(FBase):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.text = self.text
            self.ui.on_click = self._clicked
            self.ui.update()
        else:
            self.ui = ft.ElevatedButton(text=self.text, on_click=self._clicked, expand=self.layout_weight)
