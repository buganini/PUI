from .. import *
from .base import *
import asyncio

class UApplication(PUIView):
    def __init__(self):
        super().__init__()
        self._palette = [
            # http://urwid.org/reference/display_modules.html#urwid.BaseScreen.register_palette
            # name,          fg,    bg,         mono, fg_high, bg_high
            ('btn',         'white','dark blue'),
            ('btn:focus',   'white','dark red','bold'),
            ('pb:normal',   '',     'dark gray'),
            ('pb:complete', '',     'white'),
        ]
        self.ui = urwid.Filler( urwid.Text(""))
        self.loop = asyncio.get_event_loop()

    def redraw(self):
        self.loop.call_soon(self.update)

    def addChild(self, idx, child):
        if idx>0:
            raise RuntimeError("Urwid only support single window")
        self.ui.set_body(child.ui)

    def on_unhandled_input(self, key):
        pass

    def palette(self, p):
        self._palette = p

    def start(self):
        self.urwid_loop = urwid.MainLoop(
            urwid.Frame(self.ui),
            event_loop=urwid.AsyncioEventLoop(loop=self.loop),
            palette=self._palette,
            unhandled_input=self.on_unhandled_input
        )
        self.urwid_loop.run()
