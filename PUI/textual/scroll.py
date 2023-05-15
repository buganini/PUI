from .. import *
from .base import *

class TScroll(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.ScrollableContainer()
            self.ui.set_styles("height: 100h;")

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        child.tremove()
