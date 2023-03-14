from .. import *
from .base import *

class UColumns(UBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = urwid.Columns([])

    def addChild(self, idx, child):
        self.ui.contents.append((child.ui, self.ui.options()))

    def removeChild(self, idx, child):
        self.ui.contents.pop(idx)


class UPile(UBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = urwid.Pile([])

    def addChild(self, idx, child):
        self.ui.contents.append((child.ui, self.ui.options()))

    def removeChild(self, idx, child):
        self.ui.contents.pop(idx)
