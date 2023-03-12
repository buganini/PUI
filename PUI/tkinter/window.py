from .. import *
import tkinter as tk

class TkWindow(PUIView):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    def update(self):
        if not hasattr(self, "window"):
            import tkinter as tk
            self.window = tk.Tk()
        if not self.title is None:
            self.window.title(self.title)
        if not self.size is None:
            self.window.geometry("x".join([str(v) for v in self.size]))
        self.window.resizable(False, False)
        self.window.iconbitmap('icon.ico')

        super().update()

    def addChild(self, child):
        if child.layout=="pack":
            child.ui.pack(side=child.side, **child.kwargs)
        elif child.layout=="grid":
            child.ui.grid(**child.kwargs)
        elif child.layout=="place":
            child.ui.place(*child.kwargs)
        else:
            print("addChild: Unknown layout", child.layout)

    def removeChild(self, child):
        if child.layout=="pack":
            child.ui.pack_forget()
        elif child.layout=="grid":
            child.ui.grid_forget()
        elif child.layout=="place":
            child.ui.place_forget()
        else:
            print("removeChild: Unknown layout", child.layout)

    def start(self):
        self.window.mainloop()
