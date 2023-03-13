from .. import *
from .base import *

class FRow(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Row()

    def addChild(self, child):
        self.ui.controls.append(child.ui)
        self.ui.update()

    def removeChild(self, child):
        self.ui.controls.remove(child.ui)
        self.ui.update()

class FColumn(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Column()

    def addChild(self, child):
        self.ui.controls.append(child.ui)
        self.ui.update()

    def removeChild(self, child):
        self.ui.controls.remove(child.ui)
        self.ui.update()
