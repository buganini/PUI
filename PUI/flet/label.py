from .. import *
from .base import *

class Label(FBase):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ft.Text(spans=[])
        self.ui.expand = self.layout_weight
        if self._onClicked:
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
        super().update(prev)