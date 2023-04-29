from .. import *
from .base import *

class TkWindow(TkBaseWidget):
    def __init__(self, title=None, size=None, resizable=None):
        super().__init__()
        self.title = title
        self.size = size
        self.resizable = resizable

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = tk.Toplevel(self.parent.ui)

        if not self.title is None:
            self.ui.title(self.title)
        if not self.size is None:
            self.ui.geometry("x".join([str(v) for v in self.size]))

        if type(self.resizable) is bool:
            resizable = (self.resizable, self.resizable)
        elif self.resizable:
            resizable = self.resizable
        else:
            resizable = (True, True)
        self.ui.resizable(*resizable)
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
