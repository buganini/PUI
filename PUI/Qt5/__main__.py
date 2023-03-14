from . import *

data = State()
class Example(Window):
    def __init__(self):
        super().__init__(title="blah")
        data.var = 0

    def content(self):
        with VBox():
            with HBox():
                Button("-", self.on_minus)
                Label(f"{data.var}")
                Button("+", self.on_plus)

            with HBox():
                for i in range(0, data.var):
                    Label(f"{i}")

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
