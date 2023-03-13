import sys
sys.path.append("..")
from PUI import State
from PUI.flet import *

data = State()
class FExample(FWindow):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 0

    def content(self):
        with FColumn() as scope:
            with FRow() as scope:
                FElevatedButton("-", self.on_minus)
                FText(f"{data.var}")
                FElevatedButton("+", self.on_plus)

            with FRow() as scope:
                for i in range(0, data.var):
                    FText(f"{i}")

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = FExample()
root.run()
