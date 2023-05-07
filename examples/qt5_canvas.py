import sys
sys.path.append("..")
from PUI.Qt5 import *

data = State()
data.var = 50

class QtExample(QtApplication):
    def content(self):
        with QtWindow(title="blah", size=(640,480)):
            with QtVBox() as scope:
                with QtCanvas() as canvas:
                    QtCanvasText(data.var, data.var/2, f"blah {data.var}")
                    QtCanvasLine(data.var, data.var, data.var*2, data.var*3)
                with QtHBox() as scope:
                    QtButton("-", self.on_minus)
                    QtLabel(f"{data.var}")
                    QtButton("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = QtExample()
root.run()
