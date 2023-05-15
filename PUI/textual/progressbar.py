from .. import *
from .base import *

class TProgressBar(TBase):
    def __init__(self, progress, maximum=1):
        super().__init__()
        self.progress = progress*100
        self.maximum = maximum*100

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = widgets.ProgressBar(total=self.maximum, show_eta=False)
        self.ui.update(total=self.maximum)
        self.ui.progress = self.progress