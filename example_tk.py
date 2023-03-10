from PUI.tkinter import *

class TkExample(TkWindow):
    def content(self):
        TkButton("blah")

root = TkExample()
root.run()