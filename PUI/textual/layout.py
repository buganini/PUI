from .. import *
from .base import *

class TVertical(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Vertical()

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        self.inner[idx].remove()

class THorizontal(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Horizontal()

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        self.inner[idx].remove()
