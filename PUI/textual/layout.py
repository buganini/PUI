from .. import *
from .base import *

class TVertical(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Vertical()
        self.content_width = True
        self.content_height = True

    def addChild(self, idx, child):
        self.inner.mount(child.outer)
        if child.layout_weight:
            child.content_height = False
            child.t_update_layout()
        self.content_width = self.content_width and get_child_content_width(child)
        self.content_height = self.content_height and get_child_content_height(child)
        self.t_update_layout()

    def removeChild(self, idx, child):
        child.tremove()

class THorizontal(TBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = containers.Horizontal()
            self.ui.set_styles("width: auto; height: auto;")

    def addChild(self, idx, child):
        self.inner.mount(child.outer)
        if child.layout_weight:
            child.content_width = False
            child.t_update_layout()
        self.content_width = self.content_width and get_child_content_width(child)
        self.content_height = self.content_height and get_child_content_height(child)
        self.t_update_layout()

    def removeChild(self, idx, child):
        child.tremove()

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
