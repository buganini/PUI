import sys
sys.path.append("..")
from PUI.PySide6 import *

data = State()
data.var = 50

class QtExample(QtApplication):
    def content(self):
        with QtWindow(title="blah", size=(640,480)):
            with QtVBox():
                QtCanvas(self.painter, data.var)
                with QtHBox():
                    QtButton("-").click(self.on_minus)
                    QtLabel(f"{data.var}")
                    QtButton("+").click(self.on_plus)

    @staticmethod
    def painter(canvas, var):
        canvas.drawText(var, var/2, f"blah {var}")
        canvas.drawLine(var, var, var*2, var*3)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = QtExample()
root.run()
