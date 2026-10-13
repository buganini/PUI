import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tkinter", "PySide6", "flet", "textual", "wx"])

print(backend)
if backend == "tkinter":
    from PUI.tkinter import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
elif backend == "textual":
    from PUI.textual import *
elif backend == "wx":
    from PUI.wx import *
else:
    raise RuntimeError(f"Unknown backend {backend}")

data = State()
data.var = 5

class Example(Application):
    def on_minus(self, event):
        data.var -= 1

    def on_plus(self, event):
        data.var += 1

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

root = Example()
root.run()
