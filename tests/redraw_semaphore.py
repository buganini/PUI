import sys
sys.path.append("..")

from PUI.PySide6 import *
import time

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()

        self.redraw_cnt = 0
        self.content_cnt = 0

    def redraw(self):
        self.redraw_cnt += 1
        print("redraw", self.redraw_cnt)
        return super().redraw()

    def content(self):
        print("content", self.content_cnt)
        self.content_cnt += 1
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Label(f"Redraw {self.redraw_cnt}")
                with HBox():
                    Label(f"Content {self.content_cnt}")

                with HBox():
                    Button("Reset").click(self.do_reset)
                    Button("Redraw 1").click(self.do_redraw, 1)
                    Button("Redraw 1000").click(self.do_redraw, 1000)
                    Button("Redraw 10000").click(self.do_redraw, 10000)

    def do_reset(self):
        self.redraw_cnt = 0
        self.content_cnt = 0
        self.redraw()

    def do_redraw(self, n):
        for i in range(n):
            self.redraw()

root = Example()
root.run()
