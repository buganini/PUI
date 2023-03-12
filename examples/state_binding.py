import sys
sys.path.append("..")
from PUI import State
from PUI.tkinter import *
import functools

data = State()
class TkExample(TkWindow):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 0

    def content(self):
        with TkVBox() as scope:
            with TkHBox() as scope:
                TkButton("-", self.on_minus)
                TkLabel(f"{data.var}")
                TkButton("+", functools.partial(self.on_plus, data("var")))
            
            with TkHBox() as scope:
                for i in range(0, data.var):
                    TkLabel(f"{i}", layout="pack", side="left")

    def on_minus(self):
        data.var -= 1

    def on_plus(self, mutable):
        mutable.value += 1

root = TkExample()
root.run()
