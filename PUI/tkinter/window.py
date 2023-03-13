from .. import *
import tkinter as tk

class TkWindow(PUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    def update(self):
        if not hasattr(self, "ui") or not self.ui:
            import tkinter as tk
            self.ui = tk.Tk()
        if not self.title is None:
            self.ui.title(self.title)
        if not self.size is None:
            self.ui.geometry("x".join([str(v) for v in self.size]))
        self.ui.resizable(False, False)
        self.ui.iconbitmap('icon.ico')

        super().update()

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

    def start(self):
        self.ui.mainloop()
