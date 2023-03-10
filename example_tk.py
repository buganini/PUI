from PUI.tkinter import *

class TkExample(TkWindow):
    def content(self):
        TkButton("btn1", self.onclick, layout="pack", side="left")
        TkButton("btn2", self.onclick, layout="pack", side="left")

    def onclick(self):
        print("click")

root = TkExample()
root.run()