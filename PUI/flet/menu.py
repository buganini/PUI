"""Flutter menu controls rendered inside the application window."""
from .base import *


class _MenuChildren:
    def addChild(self, idx, child):
        if not isinstance(child, (Menu, MenuAction)):
            raise TypeError('Menu children must be Menu or MenuAction')
        self.ui.controls.insert(idx, child.ui)

    def removeChild(self, idx, child):
        self.ui.controls.remove(child.ui)


class MenuBar(_MenuChildren, FBase):
    def __init__(self, *, native=True):
        super().__init__()
        self.native = native  # Accepted; Flet's MenuBar is an in-window control.
        self.layout_weight = 0

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.MenuBar(controls=[])
        super().update(prev)


class Menu(_MenuChildren, PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.SubmenuButton(controls=[])
        self.ui.content = self.text
        super().update(prev)


class MenuAction(PUINode):
    pui_terminal = True

    def __init__(self, text, *, native=True):
        super().__init__()
        self.text, self.native = text, native
        self.onTriggered = None

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.MenuItemButton()
        self.ui.content = self.text
        self.ui.on_click = self._triggered
        super().update(prev)

    def trigger(self, callback, *args, **kwargs):
        self.onTriggered = callback, args, kwargs
        return self

    def _triggered(self, event=None):
        node = self.get_node()
        if not node.destroyed:
            FBase._preClicked(node)
            if node.onTriggered:
                callback, args, kwargs = node.onTriggered
                callback(*args, **kwargs)
