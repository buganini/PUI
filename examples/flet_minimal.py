import sys
sys.path.append("..")
from PUI import State
from PUI.flet import *

data = State()
data.var = 0
class FExample(FApplication):
    def content(self):
        with FWindow(title="blah"):
            with FColumn():
                with FRow():
                    FElevatedButton("-", self.on_minus)
                    FText(f"{data.var}")
                    FElevatedButton("+", self.on_plus)

                with FRow():
                    for i in range(0, data.var):
                        FText(f"{i}")

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = FExample()
root.run()
