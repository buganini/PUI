import sys
sys.path.append("..")
from PUI import State
from PUI.PySide6 import *


data = State()
class QtExample(QtWindow):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 0

    def content(self):
        with QtVBox() as scope:
            with QtHBox() as scope:
                QtButton("-", self.on_minus)
                QtLabel(f"{data.var}")
                QtButton("+", self.on_plus)

            QtLineEdit(data("var")) # binding

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = QtExample()
root.run()
