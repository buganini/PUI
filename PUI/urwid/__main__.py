from .import *

data = State()
data.var = 50

class UExample(UWindow):
    def content(self):
        with HBox():
            Button("-", self.on_minus)
            Label(f"{data.var}")
            Button("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = UExample()
root.run()