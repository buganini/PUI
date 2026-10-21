from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *

class VBox(_BoxMixin, TBase):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 2
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = containers.Vertical()
            self.ui.styles.align_horizontal = 'left'
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer, before=idx)

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()

    def moveChild(self, source, target, child):
        if isinstance(child, TBase):
            if source < target:
                self.inner.move_child(child.outer, after=target)
            elif source > target:
                self.inner.move_child(child.outer, before=target)

class Stack(VBox):
    """Reverse VBox fallback: later children appear above earlier children."""

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer, before=len(self.inner.children) - idx)

    def moveChild(self, source, target, child):
        last = len(self.inner.children) - 1
        super().moveChild(last - source, last - target, child)


class HBox(_BoxMixin, TBase):
    container_x = True
    expand_x_prio = 2
    expand_y_prio = 1
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = containers.Horizontal()
            self.ui.styles.align_vertical = 'middle'
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TBase):
            self.inner.mount(child.outer, before=idx)

    def removeChild(self, idx, child):
        if isinstance(child, TBase):
            child.tremove()

    moveChild = VBox.moveChild

class Spacer(TBase):
    def __init__(self):
        super().__init__()
        self.tlayout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.Static("")
        super().update(prev)


class _AdaptiveLayout(HBox):
    def update(self, prev):
        super().update(prev)
        self.ui.styles.layout = 'horizontal' if self.container_x else 'vertical'
        self.ui.styles.align_horizontal = 'left'
        self.ui.styles.align_vertical = 'middle' if self.container_x else 'top'


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
