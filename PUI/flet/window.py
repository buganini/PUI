from .. import *
from .base import *

class Window(FBase):
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.maximize = maximize
        self.fullscreen = fullscreen
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
