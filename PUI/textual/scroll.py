from .. import *
from .base import *

class TScroll(TBase):
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        super().__init__()

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.ScrollableContainer()
        v = "auto"
        if self.vertical is True:
            v = "scroll"
        elif self.vertical is False:
            v = "hidden"
        h = "auto"
        if self.horizontal is True:
            h = "scroll"
        elif self.horizontal is False:
            h = "hidden"
        self.ui.set_styles(f"overflow-x: {h}; overflow-y: {v};")

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        child.tremove()
