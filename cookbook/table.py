from .config import *


state = State()
state.a1 = "A1"
state.b1 = "B1"

class TableExample(PUIView):
    def content(self):
        with VBox():
            Label(f"A1: {state.a1}")
            Label(f"B1: {state.b1}")
            with Table():
                with TableNode():
                    TableNode(state.a1).set(self.on_set, 0, 0)
                    TableNode("A2")
                    TableNode("A3")
                with TableNode():
                    TableNode(state("b1"))
                    TableNode("B2")
                    TableNode("B3")

    def on_set(self, data, *args):
        print("on_set", data, args)
        state.a1 = data