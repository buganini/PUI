from .. import *
from .base import *

class ProgressBar(FBase):
    def __init__(self, progress, maximum=100):
        super().__init__()
        self.progress = progress
        self.maximum = maximum

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.progress / self.maximum
        else:
            self.ui = ft.ProgressBar(width=300) # XXX
            self.ui.value = self.progress / self.maximum
        self.ui.expand = self.layout_weight
        try:
            self.ui.update()
        except:
            pass
        super().update(prev)
