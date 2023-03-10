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

    def addUI(self, ui):
        ui.pack()

    def start(self):
        self.window.mainloop()