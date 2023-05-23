from .. import *
from .base import *

class FProgressBar(FBase):
    def __init__(self, progress, maximum=100):
        super().__init__()
        self.progress = progress
        self.maximum = maximum

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.value = self.progress / self.maximum
            self.ui.update()
        else:
            self.ui = ft.ProgressBar()
            self.ui.value = self.progress / self.maximum
