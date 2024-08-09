import sys
sys.path.append("..")

from PUI.PySide6 import *
import time

n = 2

data = State()
data.destroyed = [False] * n
data.destroyed_id = [False] * n

class Subview(PUIView):
    def __init__(self, ident):
        super().__init__()
        self.ident = ident

    def content(self):
        print(f"content {self.ident}")
        print(f"Subview{self.ident}.content")
        Label(f"Subview{self.ident}")

class Example(Application):
    def __init__(self, icon=None):
        super().__init__(icon)

    def content(self):
        with Window(title="blah"):
            with VBox():
                Label("Without Id")

                for i in range(n):
                    if not data.destroyed[i]:
                        Subview(i)

                with HBox(): 
                    for i in range(n):
                        Button(f"Destroy {i}").click(self.do_test, i)
             
                Label("Expect: Subview be gone")
                Label("Misbehavior: Subview become standalone window")

    def do_test(self, e, i):
        data.destroyed[i] = not data.destroyed[i]

    def do_test_id(self, e, i):
        data.destroyed_id[i] = not data.destroyed_id[i]

root = Example()
root.run()
