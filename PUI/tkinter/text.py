from .. import *
from .base import *

class Text(TkBaseWidget):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.config(text = self.text)
        else:
            self.ui = tk.Label(self.tkparent.inner, text=self.text, anchor="w", justify="left")

class Html(Text):
    supported = False

class MarkDown(Text):
    supported = False
