from .. import *
from .base import *

class FScroll(FBase):
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.widget = None
        super().__init__()

    def update(self, prev):
        if prev and hasattr(prev, "hframe"):
            self.vframe = prev.vframe
            self.hframe = prev.hframe
            self.vframe.update()
        else:
            self.vframe = ft.Column() # outer
            self.hframe = ft.Row() # inner
            self.vframe.controls.append(self.hframe)
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
