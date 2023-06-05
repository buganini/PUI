from .. import *
from .base import *

class TVertical(TBase):
    container_y = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = containers.Vertical()
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer, before=idx)
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()
        else:
            self.removeChild(idx, child.children[0])

class THorizontal(TBase):
    container_x = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = containers.Horizontal()
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer, before=idx)
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()
        else:
            self.removeChild(idx, child.children[0])

class TSpacer(TBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.Static("")
        super().update(prev)