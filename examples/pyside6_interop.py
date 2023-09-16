import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tkinter", "PySide6", "flet", "textual"])

from PUI.PySide6 import *
from PySide6 import QtCore, QtWidgets, QtGui

class PuiView(PuiInQt):
    def content(self):
        with TimelineView(1):
            with VBox():
                Label("test")
                Label(str(int(time.time())))

data = State()

class Example():
    def __init__(self):
        self.app = QtWidgets.QApplication([])
        self.sub = PuiView(Window())
        data.var = 0

    def run(self):
        self.sub.redraw()
        self.app.exec()

root = Example()
root.run()
