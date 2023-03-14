from .. import *
from .base import *

class UWindow(PUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    def addChild(self, idx, child):
        if not hasattr(self, "ui") and self.ui:
            self.ui.set_body(child.ui)
        else:
            self.ui = urwid.Filler(child.ui)
            self.loop = urwid.MainLoop(urwid.Frame(self.ui))

    def start(self):
        self.loop.run()
