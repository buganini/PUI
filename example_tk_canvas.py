from PUI import State
from PUI.tkinter import *


data = State()
class TkExample(TkWindow):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 0

    def content(self):
        with TkVBox() as scope:
            with TkCanvas() as canvas:
                TkCanvasText(data.var, data.var, f"blah {data.var}")
                TkCanvasLine(0, 0, data.var, data.var*2)
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
