from .. import *
from .base import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator

class QtApplicationSignal(QtCore.QObject):
    quit = QtCore.Signal()

class Application(QtPUIView):
    def __init__(self, icon=None, *, title=''):
        super().__init__()
        self.title = title
        self.ui = None
        self.icon = icon
        self._qtappsignal = QtApplicationSignal()
        self._qtappsignal.quit.connect(self._quit, QtCore.Qt.ConnectionType.QueuedConnection) # Use QueuedConnection to prevent nested trigger

    def redraw(self):
        if self.ui:
            super().redraw()
        else:
            self.sync()

    def update(self, prev=None):
        if not self.ui:
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QApplication([])
            if self.icon:
                self.ui.setWindowIcon(QtGui.QIcon(self.icon))

        if self.title:
            self.ui.setApplicationDisplayName(self.title)
        super().update(prev)

    def addChild(self, idx, child):
        child.outer.show()

    def removeChild(self, idx, child):
        child.outer.close()

    def run(self, **kwargs):
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex=None, claude=None):
        from ..ai.native import start
        return start(self, 'PySide6', lambda: self.ui.exec(), landlock=landlock, codex=codex, claude=claude)

    def quit(self):
        if not self.destroyed and not self.retired_by:
            self._qtappsignal.quit.emit()

    def _quit(self):
        if not self.destroyed and self.ui is not None:
            self.ui.quit()

def PUIApp(func):
    """Deprecated: subclass Application and implement content() instead."""
    _warn_deprecated_decorator('PUIApp', 'Application')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIAppWrapper(Application):
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIAppWrapper(func.__name__)
        return ret

    return func_wrapper
