from .. import *
from .base import *

class Application(WxPUIView):
    def __init__(self):
        super().__init__()
        self.ui = None

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
