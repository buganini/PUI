import sys
sys.path.append("..")

from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        self.redraw_cnt = 0
        data.var = 1

    def redraw(self):
        self.redraw_cnt += 1
        print("redraw", self.redraw_cnt)
        return super().redraw()

    def content(self):
        with Window(title="blah"):
            with VBox():
                Label(f"Redraw {self.redraw_cnt}")
                Label(f"Data {data.var}")

                with HBox():
                    Button("Reset").click(self.do_reset)
                    Button("Mutate").click(self.on_mutate)
                    Button("Batched Mutate").click(self.on_batched_mutate)

                Label("Except: [Batched Mutate] triggered redraw > [Mutate] triggered redraw")

    def do_reset(self, e):
        self.redraw_cnt = 0
        data.var = 1

    def on_mutate(self, e):
        data.var += 1
        data.var += 1

    def on_batched_mutate(self, e):
        with data:
            data.var += 1
            data.var += 1

root = Example()
root.run()
