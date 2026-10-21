from textual.widgets import Rule

from .base import TBase


class Divider(TBase):
    def __init__(self) -> None:
        super().__init__()

    def update(self, prev):
        vertical = bool(getattr(self.tparent, 'container_x', False))
        self.expand_x_prio = 0 if vertical else 1
        self.expand_y_prio = 1 if vertical else 0
        orientation = 'vertical' if vertical else 'horizontal'
        self.ui = prev.ui if prev is not None else Rule(orientation)
        self.ui.orientation = orientation
        super().update(prev)

    def t_update_layout(self):
        if self.ui is None:
            return
        # A retained virtual view may skip update() when its parent changes axis.
        vertical = bool(getattr(self.tparent, 'container_x', False))
        self.ui.orientation = 'vertical' if vertical else 'horizontal'
        # w/h fill the parent's content area without fr's expansion of auto-sized
        # ancestors. Leave the theme's line color and margins on the native Rule.
        self.ui.styles.width = self.tlayout_width if self.tlayout_width is not None else (1 if vertical else '100w')
        self.ui.styles.height = self.tlayout_height if self.tlayout_height is not None else ('100h' if vertical else 1)
