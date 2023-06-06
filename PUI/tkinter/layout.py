from .. import *
from .base import *

class TkHBox(TkBaseWidget):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = tk.Frame(self.tkparent.inner)
            self.ui.grid_rowconfigure(0, weight=1)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TkBaseWidget):
            child.outer.grid(row=0, column=idx, sticky='nsew')
            if child.layout_weight is None:
                self.ui.grid_columnconfigure(idx, weight=0)
            else:
                self.ui.grid_columnconfigure(idx, weight=child.layout_weight, uniform=".")
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        self.ui.grid_columnconfigure(idx, weight=0)
        if isinstance(child, TkBaseWidget):
            child.outer.grid_forget()
        elif child.children:
            self.removeChild(idx, child.children[0])

class TkVBox(TkBaseWidget):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = tk.Frame(self.tkparent.inner)
            self.ui.config(bg="white")
            self.ui.grid_columnconfigure(0, weight=1)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, TkBaseWidget):
            child.outer.grid(row=idx, column=0, sticky='nsew')
            if child.layout_weight is None:
                self.ui.grid_rowconfigure(idx, weight=0)
            else:
                self.ui.grid_rowconfigure(idx, weight=child.layout_weight, uniform=".")
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        self.ui.grid_rowconfigure(idx, weight=0)
        if isinstance(child, TkBaseWidget):
            child.outer.grid_forget()
        elif child.children:
            self.removeChild(idx, child.children[0])

class TkSpacer(TkBaseWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = tk.Frame(self.tkparent.inner)
