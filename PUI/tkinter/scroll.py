from .. import *
from .base import *
from tkinter.scrolledtext import ScrolledText

class TkScroll(TkBaseWidget):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ScrolledText(self.tkparent.ui, state='disable')
            self.ui.grid(row=0, column=0, sticky='nsew')
            self.ui.config(cursor="arrow")

    def addChild(self, idx, child):
        self.ui.window_create('0.0', window=child.ui)

    def removeChild(self, idx, child):
        self.ui.delete('0.0', tk.END)