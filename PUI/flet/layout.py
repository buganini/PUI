from ..adaptive import HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .base import *


class LinearLayout(FBase):
    def __init__(self):
        super().__init__()
        if not isinstance(self.fparent, LinearLayout):
            self.layout_padding = (11, 11, 11, 11)

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.ui.controls.pop(idx)


class HBox(LinearLayout):
    container_x = True

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Row()
        super().update(prev)


class VBox(LinearLayout):
    container_y = True

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Column()
        super().update(prev)


class Stack(LinearLayout):
    pui_reversed_order = False

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Stack()
        super().update(prev)


class Spacer(FBase):
    pui_terminal = True

    def __init__(self):
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Container()
        super().update(prev)


class _AdaptiveLayout(LinearLayout):
    def update(self, prev):
        control = ft.Row if self.container_x else ft.Column
        if prev is not None and isinstance(prev.ui, control):
            self.ui = prev.ui
        else:
            # Keep PUI children and their controls; Flutter may recreate their
            # widgets when the parent changes from Row to Column or vice versa.
            self.ui = control(controls=list(prev.ui.controls) if prev is not None else [])
        super().update(prev)


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
