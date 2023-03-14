import sys
sys.path.append("..")
import random
backend = random.choice(["tk", "Qt5", "PySide6", "flet"])
print(backend)
if backend == "tk":
    from PUI.tkinter import *
elif backend == "Qt5":
    from PUI.Qt5 import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
from PUI import State


data = State()
class Example(Window):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 0

    def content(self):
        with VBox():
            with HBox():
                Button("-", self.on_minus)
                Label(f"{data.var}")
                Button("+", self.on_plus)

            TextField(data("var")) # binding

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
