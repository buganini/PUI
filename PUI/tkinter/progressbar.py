from .. import *
from .base import *

class TkProgressBar(TkBaseWidget):
    def __init__(self, progress, maximum=1):
        super().__init__()
        self.progress = progress*100
        self.maximum = maximum*100

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ttk.Progressbar(self.parent.ui)
        self.ui["maximum"] = self.maximum
        self.ui["value"] = self.progress
