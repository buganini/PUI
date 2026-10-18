from __future__ import annotations
from .. import _typing as _t
from ..refs import NodeBinder as _NodeBinder
from .base import *


class _WindowBinder(_NodeBinder):
    def _page(self, node, command):
        page = node.ui
        if page.web:
            import logging
            logging.getLogger('PUI').warning('Flet Web does not support Window.%s', command)
            return None
        return page

    def maximize(self, enabled: bool):
        self._schedule(enabled, self._maximize)

    def _maximize(self, node, enabled):
        page = self._page(node, 'maximize')
        if page is not None:
            page.window.maximized = enabled
            page.update()

    def minimize(self, enabled: bool):
        self._schedule(enabled, self._minimize)

    def _minimize(self, node, enabled):
        page = self._page(node, 'minimize')
        if page is not None:
            page.window.minimized = enabled
            page.update()

    def fullscreen(self, enabled: bool):
        self._schedule(enabled, self._fullscreen)

    def _fullscreen(self, node, enabled):
        page = self._page(node, 'fullscreen')
        if page is not None:
            page.window.full_screen = enabled
            page.update()


class Window(FBase):
    def __pui_binder__(self):
        app = self.root.application()
        loop, context = app.loop, app.context
        return _WindowBinder(self,
                             lambda callback: loop.call_soon_threadsafe(callback, context=context.copy()))

    def __init__(
        self,
        title: str | None = None,
        icon: _t.Any = None,
        size: tuple[int, int] | None = None,
        maximize: bool | None = None,
        fullscreen: bool | None = None,
    ) -> None:
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
        title = window_title(self)
        if title is not None:
            self.ui.title = title
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
        self._initial_maximize = enabled
        return self

    def fullscreen(self, enabled=True):
        self._initial_fullscreen = enabled
        return self
