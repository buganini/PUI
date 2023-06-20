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

import time
from datetime import datetime
class Example(Application):
    def __init__(self):
        super().__init__()

    def content(self):
        with Window(title="Window 1"):
            Label("Window 1")
        with Window(title="Window 2"):
            Label("Window 2")

root = Example()
root.run()
