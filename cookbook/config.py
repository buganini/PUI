import sys
import os

backend = os.environ.get("PUI_BACKEND") or (sys.argv[1] if len(sys.argv) > 1 else "PySide6")

if backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "textual":
    from PUI.textual import *
elif backend == "flet":
    from PUI.flet import *
elif backend == "tkinter":
    from PUI.tkinter import *
elif backend == "wx":
    from PUI.wx import *
elif backend == "web":
    from PUI.web import *
