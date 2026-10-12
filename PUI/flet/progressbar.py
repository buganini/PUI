from .. import *
from .base import *

class ProgressBar(FBase):
    def __init__(self, progress, maximum=1):
        super().__init__()
        self.progress = progress
        self.maximum = maximum

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ft.ProgressBar()
        self.ui.value = None if self.maximum == 0 else max(0, min(1, self.progress / self.maximum))
        self.ui.expand = self.layout_weight
        super().update(prev)
