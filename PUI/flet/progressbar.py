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
            self.ui = ft.ProgressBar(width=300) # XXX
        self.ui.value = max(self.progress / self.maximum, 0)
        self.ui.expand = self.layout_weight
        try:
            self.ui.update()
        except:
            pass
        super().update(prev)
