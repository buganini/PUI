import sys
sys.path.append("..")
import random
import PUI
PUI.BACKEND = random.choice(["Tk", "Qt"])
from PUI import State
from PUI.generic import *


data = State()
class Example(Window):
    def __init__(self):
        super().__init__(title="blah", size=(640,480))
        data.var = 50

    def content(self):
        with VBox() as scope:
            with Canvas() as canvas:
                CanvasText(data.var, data.var/2, f"blah {data.var}")
                CanvasLine(data.var, data.var, data.var*2, data.var*3)
            with HBox() as scope:
                Button("-", self.on_minus)
                Label(f"{data.var}")
                Button("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
