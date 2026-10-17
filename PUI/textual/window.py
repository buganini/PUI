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
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
