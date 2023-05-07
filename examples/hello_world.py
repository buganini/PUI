import sys; sys.path.append("..")

from PUI import State
from PUI.PySide6 import *

class Example(Application):
    def content(self):
        with Window(title="test", size=(640,480)):
            Label("Hellow world")

root = Example()
root.run()
