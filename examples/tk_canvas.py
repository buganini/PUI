import sys
sys.path.append("..")
from PUI.tkinter import *

data = State()
data.var = 50

class TkExample(TkApplication):
    def content(self):
        with TkWindow(title="blah"):
            with TkVBox():
                TkCanvas(self.drawCanvas, data.var)
                with TkHBox():
                    TkButton("-", self.on_minus)
                    TkLabel(f"{data.var}").layout(weight=1)
                    TkButton("+", self.on_plus)

    @staticmethod
    def drawCanvas(canvas, var):
        canvas.drawText(var, var/2, f"blah {var}")
        canvas.drawLine(var, var, var*2, var*3)
        canvas.drawPolyline([(10,50),(50,10),(70,70),(10,50)])

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = TkExample()
root.run()
