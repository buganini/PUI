from .. import *
from .base import *

class TkHBox(TkBaseWidget):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            import tkinter as tk
            self.ui = tk.Frame(self.parent.ui, **self.kwargs)

    def addChild(self, child):
        child.ui.pack(side="left")

    def removeChild(self, child):
        child.ui.pack_forget()

    def start(self):
        self.window.mainloop()

class TkVBox(TkBaseWidget):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            import tkinter as tk
            self.ui = tk.Frame(self.parent.ui, **self.kwargs)

    def addChild(self, child):
        child.ui.pack(side="top")

    def removeChild(self, child):
        child.ui.pack_forget()

    def start(self):
        self.window.mainloop()


