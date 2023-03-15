import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tk", "Qt5", "PySide6", "flet", "urwid"])

print(backend)
if backend == "tk":
    from PUI.tkinter import *
elif backend == "Qt5":
    from PUI.Qt5 import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
elif backend == "urwid":
    from PUI.urwid import *
else:
    print("Unknown backend:", backend)
    sys.exit(1)
from PUI import State

import reloadium

# reloadium: after_reload
def after_reload(actions):
    PUIView.reload()

data = State()
class Example(Window):
    def __init__(self):
        super().__init__(title="blah")
        data.list = []

    def content(self):
        with VBox():
            with HBox():
                Button("Pop", self.on_pop)
                Label(f"{len(data.list)}")
                Button("Push", self.on_push)

            for it in data.list:
                Label(f"{it}")

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
