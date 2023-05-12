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

    def _clicked(self, *_):
        node = self
        while node.retired_by:
            node = node.retired_by
        if node.onClicked:
            node.onClicked(*self.click_args, **self.click_kwargs)

    def click(self, callback, *cb_args, **cb_kwargs):
        self.onClicked = callback
        self.click_args = cb_args
        self.click_kwargs = cb_kwargs
