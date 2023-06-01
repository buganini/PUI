from .. import *
from .base import *

class TVertical(TBase):
    container_y = True
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Vertical()

    @property
    def content_width(self):
        for child in self.children:
            cw = get_child_content_width(child)
            if not cw is None and not cw:
                return False
        return True

    @property
    def content_height(self):
        for child in self.children:
            ch = get_child_content_height(child)
            if not ch is None and not ch:
                return False
        return True

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer)
            child.t_update_layout()
            self.t_update_layout()
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
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Horizontal()
            self.ui.set_styles("width: auto; height: auto;")

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer)
            child.t_update_layout()
            self.t_update_layout()
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
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = widgets.Static("")
        self.t_update_layout()
