from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .base import *


class LinearLayout(FBase):
    def __init__(self):
        super().__init__()
        if not isinstance(self.fparent, LinearLayout):
            self.layout_padding = (11, 11, 11, 11)

    def postSync(self):
        super().postSync()
        from ..expansion import physical_children, priority
        if not (getattr(self, 'container_x', False) or getattr(self, 'container_y', False)):
            return
        axis = 'x' if getattr(self, 'container_x', False) else 'y'
        children = list(physical_children(self))
        highest = max((priority(child, axis, self) for child in children), default=0)
        for child in children:
            if child.shell is not None:
                grows = highest > 0 and priority(child, axis, self) == highest
                child.shell.expand = (child.layout_weight or 1) if grows else None

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.ui.controls.pop(idx)


class HBox(_BoxMixin, LinearLayout):
    expand_x_prio, expand_y_prio = 3, 1
    container_x = True

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Row()
        super().update(prev)


class VBox(_BoxMixin, LinearLayout):
    expand_x_prio, expand_y_prio = 1, 3
    container_y = True

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Column()
        super().update(prev)


class Stack(LinearLayout):
    expand_x_prio = expand_y_prio = 1
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


class _AdaptiveLayout(_BoxMixin, LinearLayout):
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
