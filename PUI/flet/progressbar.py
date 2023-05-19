from .. import *
from .base import *

class FProgressBar(FBase):
    def __init__(self, progress, maximum=1):
        super().__init__()
        self.progress = progress*100
        self.maximum = maximum*100

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.value = self.progress / self.maximum
            self.ui.update()
        else:
            self.ui = ft.ProgressBar()
            self.ui.value = self.progress
