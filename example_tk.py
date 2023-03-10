from PUI.tkinter import *

class TkExample(TkWindow):
    def content(self):
        TkButton("blah", self.onclick)

    def onclick(self):
        print("click")

root = TkExample()
root.run()