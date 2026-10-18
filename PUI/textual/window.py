from __future__ import annotations
from .. import _typing as _t
from ..refs import NodeBinder as _NodeBinder
from .. import *
import sys

class _WindowBinder(_NodeBinder):
    def _warn(self, enabled, command):
        self._node(enabled)
        import logging
        logging.getLogger('PUI').warning('Textual does not support Window.%s', command)

    def maximize(self, enabled: bool):
        self._warn(enabled, 'maximize')

    def minimize(self, enabled: bool):
        self._warn(enabled, 'minimize')

    def fullscreen(self, enabled: bool):
        self._warn(enabled, 'fullscreen')


class Window(PUINode):
    def __pui_binder__(self):
        return _WindowBinder(self)

    pui_virtual = True
    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] | None = None,
        maximize: bool | None = None,
        fullscreen: bool | None = None,
    ) -> None:
        super().__init__()
