from .. import *
from .base import *

class UWindow(PUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size
        self._palette = [
            # http://urwid.org/reference/display_modules.html#urwid.BaseScreen.register_palette
            # name,          fg,    bg,         mono, fg_high, bg_high
            ('btn',         'white','dark blue'),
            ('btn:focus',   'white','dark red','bold'),
            ('pb:normal',   '',     'dark gray'),
            ('pb:complete', '',     'white'),
        ]

    def addChild(self, idx, child):
        if not hasattr(self, "ui") and self.ui:
            self.ui.set_body(child.ui)
        else:
            self.ui = urwid.Filler(child.ui)
            self.loop = urwid.MainLoop(urwid.Frame(self.ui), palette=self._palette)

    def palette(self, p):
        self._palette = p

    def start(self):
        self.loop.run()
