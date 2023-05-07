import sys; sys.path.append("..")

from PUI import State
from PUI.PySide6 import *

class Example(Application):
    def content(self):
        with Window(title="test", size=(320,240)):
            Label("Hello world")

root = Example()
root.run()
