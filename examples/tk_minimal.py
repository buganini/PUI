import sys
sys.path.append("..")
from PUI import State
from PUI.tkinter import *


data = State()
data.var = 0

class TkExample(TkApplication):
    def content(self):
        with TkWindow(title="blah"):
            with TkVBox():
                with TkHBox():
                    TkButton("-", self.on_minus)
                    TkLabel(f"{data.var}")
                    TkButton("+", self.on_plus)

                with TkHBox():
                    for i in range(0, data.var):
                        TkLabel(f"{i}", layout="pack", side="left")

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = TkExample()
root.run()
