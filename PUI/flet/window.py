from .. import *
from .base import *

class FWindow(PUINode):
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None

    def update(self, prev=None):
        self.parent.ui.title = self.title
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            return
        self.parent.ui.add(child.ui)

    def removeChild(self, idx, child):
        if idx != 0:
            return
        self.parent.ui.remove(child.ui)
