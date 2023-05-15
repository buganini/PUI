from .. import *
from .base import *

class TVertical(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Vertical()
            self.ui.set_styles("height: auto;")

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        child.tremove()

class THorizontal(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Horizontal()
            self.ui.set_styles("width: auto;")

    def addChild(self, idx, child):
        self.inner.mount(child.outer)

    def removeChild(self, idx, child):
        child.tremove()

class TSpacer(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = widgets.Static("")
            self.ui.set_styles("width: 1fr; height: 1fr;")
