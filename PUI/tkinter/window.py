from .. import *
from .base import *

class TkWindow(TkBaseWidget):
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
        else:
            self.ui = tk.Toplevel(self.parent.ui)

        if self.curr_size != self.size:
            self.curr_size = self.size
            self.ui.geometry("x".join([str(v) for v in self.size]))
        if self.curr_maximize !=  self.maximize:
            self.curr_maximize =  self.maximize

            # https://stackoverflow.com/a/70061942
            try:
                self.ui.attributes('-zoomed', True)
            except:
                self.ui.state("zoomed")

        if self.curr_fullscreen != self.fullscreen:
            self.curr_fullscreen = self.fullscreen
            self.ui.attributes('-fullscreen', True)
        if not self.title is None:
            self.ui.title(self.title)

    def addChild(self, idx, child):
        child.ui.pack(fill=tk.BOTH, expand=True)

    def removeChild(self, idx, child):
        child.ui.pack_forget()
