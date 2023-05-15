from .. import *
from .base import *

class TScroll(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.ScrollableContainer()

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        child.tremove()
