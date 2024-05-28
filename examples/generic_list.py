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
    print("Unknown backend:", backend)
    sys.exit(1)

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.list = []

    def content(self):
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Button("Pop").click(self.on_pop)
                    Button("<<").click(self.on_rot_l)
                    Label(f"{len(data.list)}")
                    Button(">>").click(self.on_rot_r)
                    Button("Push").click(self.on_push)

                for it in data.list:
                    Label(f"{it}").tag(it)

                # Spacer()

    def on_rot_l(self):
        try:
            e = data.list.pop(0)
            data.list.append(e)
        except:
            pass

    def on_rot_r(self):
        try:
            e = data.list.pop(-1)
            data.list.insert(0, e)
        except:
            pass

    def on_pop(self):
        try:
            data.list.pop(0)
        except:
            pass

    def on_push(self):
        import string
        import random
        data.list.append(str(len(data.list))+'.'+''.join(random.choices(string.ascii_uppercase + string.digits, k=10)))

root = Example()
root.run()
