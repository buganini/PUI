from .. import *
from .base import *

class Window(TkBaseWidget):
    pui_terminal = False
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.maximize = maximize
        self.fullscreen = fullscreen

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
        else:
            self.ui = tk.Toplevel(self.parent.inner)
            # self.ui.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.curr_size = Prop()
            self.curr_maximize = Prop()
            self.curr_fullscreen = Prop()

        if self.curr_size.set(self.size):
            self.ui.geometry("x".join([str(v) for v in self.size]))

        if self.curr_maximize.set(self.maximize):
            # https://stackoverflow.com/a/70061942
            try:
                self.ui.attributes('-zoomed', True)
            except:
                self.ui.state("zoomed")

        if self.curr_fullscreen.set(self.fullscreen):
            self.ui.attributes('-fullscreen', True)

        if not self.title is None:
            self.ui.title(self.title)

    def on_closing(self):
        self.get_node().tkparent.ui.destroy()

    def addChild(self, idx, child):
        if idx:
            return
        child.outer.pack(fill=tk.BOTH, expand=True)

    def removeChild(self, idx, child):
        child.outer.pack_forget()
