import sys

if len(sys.argv)<2 or sys.argv[1] == "PySide6":
    from PUI.PySide6 import *
elif sys.argv[1] == "textual":
    from PUI.textual import *
elif sys.argv[1] == "tk":
    from PUI.tkinter import *
