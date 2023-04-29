import sys
sys.path.append("..")
from PUI import State
from PUI.Qt5 import *


data = State()
data.var = 0
class QtExample(QtApplication):
    def content(self):
        with QtWindow(title="blah"):
            with QtVBox():
                with QtHBox():
                    QtButton("-", self.on_minus)
                    QtLabel(f"{data.var}")
                    QtButton("+", self.on_plus)

                with QtHBox():
                    for i in range(0, data.var):
                        QtLabel(f"{i}")

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = QtExample()
root.run()
