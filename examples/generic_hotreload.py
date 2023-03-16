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

import reloadium

# reloadium: after_reload
def after_reload(actions):
    PUIView.reload()

import time
from datetime import datetime
class Example(Window):
    def __init__(self):
        super().__init__(title="blah")

    def content(self):
        with TimelineView(0.5):
            with VBox():
                Label(backend)
                Label(f"{int(time.time())}")
                Label(f"{datetime.now()}")

root = Example()
root.run()
