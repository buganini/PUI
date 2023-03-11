import sys
sys.path.append("..")
from PUI import State
from PUI.tkinter import *


data = State()
class TkExample(TkWindow):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 50

    def content(self):
        with TkVBox() as scope:
            with TkCanvas() as canvas:
                TkCanvasText(data.var, data.var/2, f"blah {data.var}")
                TkCanvasLine(data.var, data.var, data.var*2, data.var*3)
            with TkHBox() as scope:
                TkButton("-", self.on_minus)
                TkLabel(f"{data.var}")
                TkButton("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = TkExample()
root.run()
