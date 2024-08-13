from .. import *
from .base import *

class VBox(TBase):
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

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()

class HBox(TBase):
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

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()

class Spacer(TBase):
    def __init__(self):
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.Static("")
        super().update(prev)