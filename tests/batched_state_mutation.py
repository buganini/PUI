import sys
sys.path.append("..")

from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        self.count = 0
        data.var1 = 0
        data.var2 = 0

    def content(self):
        self.count += 1
        print("View Builder", self.count)
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Button("Mutate").click(self.on_mutate)
                    Label(f"{data.var1}")
                    Label(f"{data.var2}")
                    Button("Batched Mutate").click(self.on_batched_mutate)

    def on_mutate(self):
        data.var1 += 1
        data.var2 -= 1

    def on_batched_mutate(self):
        with data:
            data.var1 += 1
            data.var2 -= 1

root = Example()
root.run()
