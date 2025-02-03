from .. import *
from .base import *

class Application(WxPUIView):
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
            self.ui = wx.App()

        super().update(prev)

    def addChild(self, idx, child):
        child.outer.Show()

    def removeChild(self, idx, child):
        child.outer.Close()

    def start(self):
        self.ui.MainLoop()

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
