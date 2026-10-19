"""Shared parent-size visibility bounds and adaptive directions."""
from __future__ import annotations


def matches(size, limits):
    if size is None:
        return False
    width, height = size
    low_w, high_w, low_h, high_h = limits
    return ((low_w is None or width >= low_w) and
            (high_w is None or width < high_w) and
            (low_h is None or height >= low_h) and
            (high_h is None or height < high_h))


class AdaptiveBox:
    def _choose_direction(self, threshold, axis):
        parent = self.parent
        while parent is not None and parent.pui_virtual and parent.parent is not parent:
            parent = parent.parent
        size = None
        if threshold is not None and parent is not None and parent is not self:
            parent._ensure_size()
            parent._start_size()
            size = parent._state.size
        primary = size is not None and size[axis] >= threshold
        self.container_x = primary if axis == 0 else not primary
        self.container_y = not self.container_x
        self.expand_x_prio = 2 if self.container_x else 1
        self.expand_y_prio = 1 if self.container_x else 2


class HVBoxMixin(AdaptiveBox):
    def __init__(self, minWidth: float, *, tMinWidth: int | None = None):
        super().__init__()
        self._choose_direction(tMinWidth if self._terminal_units else minWidth, 0)


class VHBoxMixin(AdaptiveBox):
    def __init__(self, minHeight: float, *, tMinHeight: int | None = None):
        super().__init__()
        self._choose_direction(tMinHeight if self._terminal_units else minHeight, 1)
