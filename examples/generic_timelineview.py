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
    raise RuntimeError(f"Unknown backend {backend}")

import time
from datetime import datetime
class Example(Application):
    def __init__(self):
        super().__init__()

    def content(self):
        with Window(title="blah"):
            with TimelineView(0.5):
                with VBox():
                    Label(backend)
                    Label(f"{int(time.time())}")
                    Label(f"{datetime.now()}")

root = Example()
root.run()
