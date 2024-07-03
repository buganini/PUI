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
    raise RuntimeError(f"Unknown backend {backend}")

data = State()
data.var = 5

@PUIApp
def Example():
    def on_minus():
        data.var -= 1

    def on_plus():
        data.var += 1

    with Window(title="blah"):
        with VBox():
            with HBox():
                Button("-").click(on_minus)
                Label(f"{data.var}")
                Button("+").click(on_plus)

            with HBox():
                for i in range(0, data.var):
                    Label(f"{i}")

root = Example()
root.run()
