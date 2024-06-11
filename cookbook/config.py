import sys

if len(sys.argv)<2 or sys.argv[1] == "PySide6":
    from PUI.PySide6 import *
elif sys.argv[1] == "textual":
    from PUI.textual import *
elif sys.argv[1] == "flet":
    from PUI.flet import *
elif sys.argv[1] == "tkinter":
    from PUI.tkinter import *
elif sys.argv[1] == "wx":
    from PUI.wx import *
