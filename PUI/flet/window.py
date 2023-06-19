from .. import *
from .base import *

class Window(FBase):
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None
        self.child_weight = 1

    def update(self, prev=None):
        self.inner.title = self.title
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            return
        self.inner.add(child.outer)

    def removeChild(self, idx, child):
        if idx != 0:
            return
        self.inner.remove(child.outer)
