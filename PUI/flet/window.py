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
        return self._window_state('maximized', 'maximize', enabled)

    def fullscreen(self, enabled=True):
        return self._window_state('full_screen', 'fullscreen', enabled)

    def _window_state(self, attribute, initial_name, enabled):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            setattr(node, '_initial_' + initial_name, enabled)
            return self
        app = FView.application(node)
        def apply():
            current = node.get_node()
            if not current.destroyed and current.ui is not None:
                setattr(current.ui.window, attribute, bool(enabled))
                current.ui.update()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is app.loop:
            apply()
        else:
            app.loop.call_soon_threadsafe(apply, context=app.context.copy())
        return self
