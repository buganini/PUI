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
        self.ui.controls.append(child.outer)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.controls.remove(find_flet_outer(child))
        self.ui.update()

    def flet(self, alignment=None, vertical_alignment=None):
        if not alignment is None:
            self.flet_params["alignment"] = alignment
        if not vertical_alignment is None:
            self.flet_params["vertical_alignment"] = vertical_alignment
        return self

class FColumn(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Column(expand=self.layout_weight)
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.controls.append(child.outer)
        try:
            self.ui.update()
        except:
            pass

    def removeChild(self, idx, child):
        self.ui.controls.remove(find_flet_outer(child))
        self.ui.update()

    def flet(self, alignment=None, horizontal_alignment=None, **kwargs):
        if not alignment is None:
            self.flet_params["alignment"] = alignment
        if not horizontal_alignment is None:
            self.flet_params["horizontal_alignment"] = horizontal_alignment
        for k,v in kwargs.items():
            self.flet_params[k] = v
        return self


class FSpacer(FBase):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.Container()
        super().update(prev)
