from .. import *
import tkinter as tk

class TkWindow(PUIView):
    def inflate(self):
        import tkinter as tk
        self.window = tk.Tk()
        self.window.title('GUI')
        self.window.geometry('380x400')
        self.window.resizable(False, False)
        self.window.iconbitmap('icon.ico')
        return self.window

    def addChild(self, child):
        if child.layout=="pack":
            child.ui.pack(**child.kwargs)
        elif child.layout=="grid":
            child.ui.grid(**child.kwargs)
        elif child.layout=="place":
            child.ui.place(*child.kwargs)

    def start(self):
        self.window.mainloop()
