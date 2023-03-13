from .. import *
from .base import *

class TkHBox(TkBaseWidget):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            import tkinter as tk
            self.ui = tk.Frame(self.parent.ui)
            self.ui.rowconfigure(0, weight=1)

    def addChild(self, idx, child):
        child.ui.grid(row=0, column=idx, sticky='nsew')
        if not child.layout_weight is None:
            self.ui.columnconfigure(idx, weight=child.layout_weight)

    def removeChild(self, idx, child):
        child.ui.grid_forget()

class TkVBox(TkBaseWidget):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            import tkinter as tk
            self.ui = tk.Frame(self.parent.ui)
            self.ui.config(bg="white")
            self.ui.columnconfigure(0, weight=1)

    def addChild(self, idx, child):
        child.ui.grid(row=idx, column=0, sticky='nsew')
        if not child.layout_weight is None:
            self.ui.rowconfigure(idx, weight=child.layout_weight)

    def removeChild(self, idx, child):
        child.ui.grid_forget()


