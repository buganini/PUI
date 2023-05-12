import sys
sys.path.append("..")

import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tk", "PySide6", "flet"])

print(backend)
if backend == "tk":
    from PUI.tkinter import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
else:
    print("Unknown backend:", backend)
    sys.exit(1)

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 50

    def content(self):
        with Window(title="blah", size=(640,480)):
            with VBox():
                Canvas(self.painter, data.var)
                with HBox():
                    Button("-", self.on_minus)
                    Label(f"{data.var}").layout(weight=1)
                    Button("+", self.on_plus)

    @staticmethod
    def painter(canvas, var):
        canvas.drawText(var, var/2, f"blah {var}")
        canvas.drawLine(var, var, var*2, var*3)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
