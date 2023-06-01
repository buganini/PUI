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

    @property
    def fit_content_width(self):
        for child in self.children:
            cw = get_child_content_width(child)
            if not cw is None and not cw:
                return False
        return self.horizontal is False

    @property
    def fit_content_height(self):
        for child in self.children:
            ch = get_child_content_height(child)
            if not ch is None and not ch:
                return False
        return self.vertical is False

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
