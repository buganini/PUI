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
            self.ui.state('zoomed')
        if self.curr_fullscreen != self.fullscreen:
            self.curr_fullscreen = self.fullscreen
            self.ui.attributes('-fullscreen', True)
        if not self.title is None:
            self.ui.title(self.title)

        self.ui.iconbitmap('icon.ico')

    def addChild(self, idx, child):
        if child.layout=="pack":
            child.ui.pack(side=child.side, **child.kwargs)
        elif child.layout=="grid":
            child.ui.grid(**child.kwargs)
        elif child.layout=="place":
            child.ui.place(*child.kwargs)
        else:
            child.ui.pack(fill=tk.BOTH, expand=True)

    def removeChild(self, idx, child):
        if child.layout=="pack":
            child.ui.pack_forget()
        elif child.layout=="grid":
            child.ui.grid_forget()
        elif child.layout=="place":
            child.ui.place_forget()
        else:
            child.ui.pack_forget()
