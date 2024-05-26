import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tkinter", "PySide6", "flet", "textual", "Wx"])

print(backend)
if backend == "tkinter":
    from PUI.tkinter import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
elif backend == "textual":
    from PUI.textual import *
elif backend == "Wx":
    from PUI.wx import *
else:
    print("Unknown backend:", backend)
    sys.exit(1)

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 0

    def content(self):
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Button("-").click(self.on_minus)
                    Label(f"{data.var}")
                    Button("+").click(self.on_plus)

                with HBox():
                    for i in range(0, data.var):
                        Label(f"{i}")

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
