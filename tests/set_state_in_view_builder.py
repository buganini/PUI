import sys
sys.path.append("..")
from PUI import StateMutationInViewBuilderError
from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 0

    def content(self):
        print("Exepct StateMutationInViewBuilderError")
        try:
            data.var += 1
            raise RuntimeError("Should not reach here")
        except StateMutationInViewBuilderError:
            print("Got StateMutationInViewBuilderError")

        with VBox():
            Label("Check terminal output:")
            Label("Exepct StateMutationInViewBuilderError")
            Button("Close").click(self.on_close)

    def on_close(self, e):
        self.quit()

root = Example()
root.run()
