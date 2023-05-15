from .. import *
from .base import *

class TVertical(TBase):
    @property
    def ui(self):
        return containers.Vertical(*[c.outer for c in self.children])

    @ui.setter
    def ui(self, val):
        pass

class THorizontal(TBase):
    @property
    def ui(self):
        return containers.Horizontal(*[c.outer for c in self.children])

    @ui.setter
    def ui(self, val):
        pass