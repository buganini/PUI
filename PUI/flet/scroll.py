from .. import *
from .base import *
import math

class Scroll(FBase):
    END = -0.0

    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.align_x = 0
        self.align_y = 0
        self.widget = None
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        if prev and hasattr(prev, "hframe"):
            self.vframe = prev.vframe
            self.hframe = prev.hframe
        else:
            self.vframe = ft.Column() # outer
            self.hframe = ft.Row() # inner
            self.vframe.controls.append(self.hframe)
        self.vframe.expand = self.layout_weight
        if self.vertical is None:
            self.vframe.scroll = ft.ScrollMode.AUTO
        elif self.vertical:
            self.vframe.scroll = ft.ScrollMode.ADAPTIVE
        else:
            self.vframe.scroll = None
        if self.horizontal is None:
            self.hframe.scroll = ft.ScrollMode.AUTO
        elif self.horizontal:
            self.hframe.scroll = ft.ScrollMode.ADAPTIVE
        else:
            self.hframe.scroll = None
        try:
            self.vframe.update()
        except:
            pass
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            return
        self.hframe.controls.insert(idx, child.outer)
        try:
            self.hframe.update()
        except:
            pass

    def removeChild(self, idx, child):
        if idx != 0:
            return
        self.hframe.controls.pop(idx)
        self.hframe.update()

    @property
    def outer(self):
        return self.vframe

    @property
    def inner(self):
        return self.hframe

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
