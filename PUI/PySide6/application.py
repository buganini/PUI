from .. import *
from .base import *

class Application(QtPUIView):
    def __init__(self, icon=None):
        super().__init__()
        self.ui = None
        self.icon = icon

    def redraw(self):
        if self.ui:
            super().redraw()
        else:
            self.update(None)

    def update(self, prev=None):
        if not self.ui:
            from PySide6 import QtWidgets
            self.ui = QtWidgets.QApplication([])
            if self.icon:
                self.ui.setWindowIcon(QtGui.QIcon(self.icon))

        super().update(prev)

    def addChild(self, idx, child):
        child.outer.show()

    def removeChild(self, idx, child):
        child.outer.close()

    def start(self):
        self.ui.exec()

def PUIApp(func):
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
