from .. import *
from .base import *

class FRow(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Row(expand=self.layout_weight)

    def addChild(self, idx, child):
        self.ui.controls.append(child.ui)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.controls.remove(child.ui)
        self.ui.update()

class FColumn(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Column(expand=self.layout_weight)

    def addChild(self, idx, child):
        self.ui.controls.append(child.ui)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.controls.remove(child.ui)
        self.ui.update()
