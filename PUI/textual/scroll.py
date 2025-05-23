from .. import *
from .base import *
import math

class Scroll(TBase):
    END = -0.0
    scroll = True
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.align_x = 0
        self.align_y = 0
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = containers.ScrollableContainer()

        v = "auto"
        self.container_y = True
        self.expand_y_prio = 3
        if self.vertical is True:
            v = "scroll"
        elif self.vertical is False:
            v = "hidden"
            self.container_y = False
            self.expand_y_prio = 1

        h = "auto"
        self.container_x = True
        self.expand_x_prio = 3
        if self.horizontal is True:
            h = "scroll"
        elif self.horizontal is False:
            h = "hidden"
            self.container_x = False
            self.expand_x_prio = 1

        self.ui.set_styles(f"overflow-x: {h}; overflow-y: {v};")

        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer)
            self.t_update_layout()
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()
        else:
            self.removeChild(idx, child.children[0])

    def scrollX(self, pos=0):
        if math.copysign(1, pos) >= 0:
            self.align_x = 0
            self.hsb_offset = pos
        else:
            self.align_x = 1
            self.hsb_offset = abs(pos)
        return self

    def scrollY(self, pos=0):
        if math.copysign(1, pos) >= 0:
            self.align_y = 0
            self.vsb_offset = pos
        else:
            self.align_y = 1
            self.vsb_offset = abs(pos)
        return self
