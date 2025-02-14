import sys
sys.path.append("..")

from PUI.PySide6 import *
import time

data = State()

mainview_cnt = 0
subview_cnt = 0

class Subview(PUIView):
    def content(self):
        global subview_cnt
        subview_cnt += 1
        Button("Redraw subview").click(self.do_redraw)
        Label(f"subview {subview_cnt}")

    def do_redraw(self, e):
        self.redraw()

class Example(Application):
    def __init__(self):
        super().__init__()


    def content(self):
        global mainview_cnt
        mainview_cnt += 1
        with Window(title="blah"):
            with VBox():
                Button("Redraw mainview").click(self.do_redraw)
                Label(f"mainview {mainview_cnt}")
                Subview()

    def do_redraw(self, e):
        self.redraw()

root = Example()
root.run()
