import sys
sys.path.append("..")

import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tk", "Qt5", "PySide6", "flet", "urwid"])

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
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 50

    def content(self):
        with Window(title="blah", size=(640,480)):
            with VBox():
                with Canvas().layout(weight=1):
                    CanvasText(data.var, data.var/2, f"blah {data.var}")
                    CanvasLine(data.var, data.var, data.var*2, data.var*3)
                with HBox():
                    Button("-", self.on_minus)
                    Label(f"{data.var}").layout(weight=1)
                    Button("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
