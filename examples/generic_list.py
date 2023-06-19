import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tkinter", "PySide6", "flet", "textual"])

print(backend)
if backend == "tkinter":
    from PUI.tkinter import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
elif backend == "textual":
    from PUI.textual import *
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
                    Label(f"{len(data.list)}")
                    Button("Push").click(self.on_push)

                for it in data.list:
                    Label(f"{it}")

                Spacer()

    def on_pop(self):
        try:
            data.list.pop(0)
        except:
            pass

    def on_push(self):
        import string
        import random
        data.list.append(''.join(random.choices(string.ascii_uppercase + string.digits, k=10)))

root = Example()
root.run()
