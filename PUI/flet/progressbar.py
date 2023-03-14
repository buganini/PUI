from .. import *
from .base import *

class FProgressBar(FBase):
    def __init__(self, progress):
        super().__init__()
        self.progress = progress

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.value = self.progress
            self.ui.update()
        else:
            self.ui = ft.ProgressBar()
            self.ui.value = self.progress
