from .base import *


class Window(FBase):
    def __init__(self, title=None, icon=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title, self.icon, self.size = title, icon, size
        self._initial_maximize = maximize
        self._initial_fullscreen = fullscreen
        self.child_weight = 1

    def update(self, prev=None):
        parent = self.parent
        while parent is not None and not isinstance(parent.ui, ft.Page):
            if parent.parent is parent:
                raise RuntimeError('Window requires a Flet Application')
            parent = parent.parent
        self.ui = parent.ui
        if self.title is not None:
            self.ui.title = self.title
        if self.icon is not None:
            self.ui.window.icon = self.icon
        if self.size is not None:
            self.ui.window.width, self.ui.window.height = self.size
        if prev is None:
            if self._initial_maximize is not None:
                self.ui.window.maximized = bool(self._initial_maximize)
            if self._initial_fullscreen is not None:
                self.ui.window.full_screen = bool(self._initial_fullscreen)
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.ui.controls.remove(child.outer)

    def maximize(self, enabled=True):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            node._initial_maximize = enabled
        else:
            node.ui.window.maximized = bool(enabled)
            node.ui.update()
        return self

    def fullscreen(self, enabled=True):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            node._initial_fullscreen = enabled
        else:
            node.ui.window.full_screen = bool(enabled)
            node.ui.update()
        return self
