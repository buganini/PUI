from .. import *
from .base import *

class UProgressBar(UBase):
    def __init__(self, progress, done=1):
        super().__init__()
        self.progress = progress * 100
        self.done = done * 100

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.set_completion(self.progress)
        else:
            self.ui = urwid.ProgressBar('pb:normal', 'pb:complete', self.progress, self.done)
