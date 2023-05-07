import sys
sys.path.append("..")
from PUI.tkinter import *

data = State()
data.var = 50

class TkExample(TkApplication):
    def content(self):
        with TkWindow(title="blah"):
            with TkVBox():
                with TkCanvas():
                    TkCanvasText(data.var, data.var/2, f"blah {data.var}")
                    TkCanvasLine(data.var, data.var, data.var*2, data.var*3)
                with TkHBox():
                    TkButton("-", self.on_minus)
                    TkLabel(f"{data.var}").layout(weight=1)
                    TkButton("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = TkExample()
root.run()
