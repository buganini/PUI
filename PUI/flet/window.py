from .. import *
from .base import *

class FWindow(PUINode):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    def update(self, prev=None):
        self.parent.ui.title = self.title
        super().update(prev)

    def addChild(self, idx, child):
        self.parent.ui.add(child.ui)

    def removeChild(self, idx, child):
        self.parent.ui.remove(child.ui)
