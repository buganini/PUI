from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *

class ProgressBar(TBase):
    def __init__(self, progress: _t.Number, maximum: _t.Number = 1) -> None:
        super().__init__()
        self.progress = progress*100
        self.maximum = maximum*100

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.ProgressBar(total=self.maximum, show_eta=False)
        self.ui.update(total=self.maximum)
        self.ui.progress = self.progress
        super().update(prev)
