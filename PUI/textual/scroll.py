from .. import *
from .base import *

class TScroll(TBase):
    weak_expand_x = True
    weak_expand_y = True
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
        self.container_y = True
        if self.vertical is True:
            v = "scroll"
        elif self.vertical is False:
            v = "hidden"
            self.container_y = False
            self.weak_hug_y = True

        h = "auto"
        self.container_x = True
        if self.horizontal is True:
            h = "scroll"
        elif self.horizontal is False:
            h = "hidden"
            self.container_x = False
            self.weak_hug_x = True
        self.ui.set_styles(f"overflow-x: {h}; overflow-y: {v};")

        parent = self.tparent
        if parent:
            if parent.strong_expand_x:
                self.strong_expand_x = True
            if parent.strong_expand_y:
                self.strong_expand_y = True

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
