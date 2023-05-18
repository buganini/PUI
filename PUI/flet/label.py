from .. import *
from .base import *

class FLabel(FBase):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Text(spans=[], expand=self.layout_weight)
        if self.onClicked:
            self.ui.spans = [
                ft.TextSpan(self.text, on_click=self._clicked)
            ]
        else:
            self.ui.spans = [
                ft.TextSpan(self.text)
            ]
        try:
            self.ui.update()
        except:
            pass