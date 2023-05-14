from .. import *
from .base import *
class TkLabel(TkBaseWidget):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.config(text = self.text)
        else:
            self.ui = tk.Label(self.parent.ui, text=self.text, **self.kwargs)
            self.ui.bind("<Button-1>", self._clicked)
        if self.onClicked:
            self.ui.config(cursor="")
