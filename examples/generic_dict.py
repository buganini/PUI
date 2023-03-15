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
import functools

data = State()
class Example(Window):
    def __init__(self):
        super().__init__(title="blah")
        data.dict = {}

    def content(self):
        with VBox():
            with HBox():
                Button("Pop", self.on_pop)
                Button("Push", self.on_push)

            for k, v in data.dict.items():
                Button(f"{k}: {v}", functools.partial(self.on_click, k))

    def on_pop(self):
        try:
            data.dict.pop()
        except:
            pass

    def on_push(self):
        import string
        import random
        data.dict[self.gen(3)] = self.gen(10)

    def on_click(self, k):
        data.dict[k] = self.gen(10)

    def gen(self, l):
        import string
        import random
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=l))

root = Example()
root.run()
