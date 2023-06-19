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

# reloadium: after_reload
def after_reload(actions):
    PUIView.reload()

import time
from datetime import datetime
class Example(Application):
    def content(self):
        with Window(title="blah"):
            with TimelineView(0.5):
                with VBox():
                    Label(backend)
                    Label(f"{int(time.time())}")
                    Label(f"{datetime.now()}")

root = Example()
root.run()
