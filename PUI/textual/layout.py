from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *

from textual.geometry import Size, Offset
from textual.layout import Layout
from textual.layouts.horizontal import HorizontalLayout
from textual.layouts.vertical import VerticalLayout


class _GapLayout(Layout):
    name = 'pui-box-gap'

    def __init__(self, horizontal, gap):
        self.horizontal, self.gap = horizontal, int(gap)
        self.native = HorizontalLayout() if horizontal else VerticalLayout()

    def arrange(self, parent, children, size, greedy=True):
        children = [child for child in children if child.display]
        reserve = max(0, len(children) - 1) * self.gap
        available = Size(max(0, size.width-reserve), size.height) if self.horizontal else Size(size.width, max(0, size.height-reserve))
        placements = self.native.arrange(parent, children, available, greedy)
        return [p._replace(region=p.region + (Offset(i*self.gap, 0) if self.horizontal else Offset(0, i*self.gap)))
                for i, p in enumerate(placements)]


class _BoxWidget(containers.Container):
    def __init__(self):
        self.gap_layout = _GapLayout(False, 0)
        super().__init__()

    @property
    def layout(self):
        return self.gap_layout


def _set_gap(node):
    if not getattr(node, 'pui_grid_layout', False):
        node.ui.gap_layout = _GapLayout(node.container_x, node.tGap)
        node.ui.refresh(layout=True)


class VBox(_BoxMixin, TBase):
    container_y = True
    expand_x_prio = 1
    expand_y_prio = 3
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = _BoxWidget()
            self.ui.styles.align_horizontal = 'left'
        super().update(prev)
        _set_gap(self)

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
    expand_x_prio = 3
    expand_y_prio = 1
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = _BoxWidget()
            self.ui.styles.align_vertical = 'middle'
        super().update(prev)
        _set_gap(self)

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
        _set_gap(self)
        self.ui.styles.align_horizontal = 'left'
        self.ui.styles.align_vertical = 'middle' if self.container_x else 'top'


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
