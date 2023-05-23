from .. import *
from .base import *

class FRow(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Row(expand=self.layout_weight)
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.controls.pop(idx)
        self.ui.update()

class FColumn(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Column(expand=self.layout_weight)
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.controls.pop(idx)
        self.ui.update()

class FSpacer(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Container()
        super().update(prev)
