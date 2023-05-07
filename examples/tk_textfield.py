import sys
sys.path.append("..")
from PUI.tkinter import *


data = State()
data.var = 0

class TkExample(Application):
    def content(self):
        with Window(title="blah"):
            with TkVBox() as scope:
                with TkHBox() as scope:
                    TkButton("-", self.on_minus)
                    TkLabel(f"{data.var}")
                    TkButton("+", self.on_plus)

                TkEntry(data("var")) # binding

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = TkExample()
root.run()
