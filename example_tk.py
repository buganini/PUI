from PUI import State
from PUI.tkinter import *


data = State()
class TkExample(TkWindow):
    def __init__(self):
        super().__init__()
        data.var = 0

    def content(self):
        TkButton("+", self.onclick, layout="pack", side="left")
        for i in range(data.var):
            TkButton("blah", self.onclick, layout="pack", side="left")

    def onclick(self):
        print("click", data.var)
        data.var += 1

root = TkExample()
root.run()
