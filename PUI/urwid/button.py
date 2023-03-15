from .. import *
from .base import *

class UButton(UBase):
    def __init__(self, text, callback=None):
        super().__init__()
        self.text = text
        self.callback = callback

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.btn = prev.btn
            self.btn.set_label(self.text)
            self.btn.pui_cb = self.callback
        else:
            self.btn = urwid.Button(self.text, on_press=self.on_press)
            self.btn.pui_cb = self.callback
            self.ui = urwid.AttrWrap(self.btn, 'btn', 'btn:focus')

    def on_press(self, ui):
        if ui.pui_cb:
            ui.pui_cb()