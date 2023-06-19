from .. import *
from .base import *

class Button(FBase):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.text = self.text
            self.ui.on_click = self._clicked
            try:
                self.ui.update()
            except:
                pass
        else:
            self.ui = ft.ElevatedButton(text=self.text, on_click=self._clicked)
        self.ui.expand = self.layout_weight
