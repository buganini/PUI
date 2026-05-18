from .config import *


state = State()
state.a1 = "A1"
state.b1 = "B1"

class TableExample(PUIView):
    def content(self):
        with VBox():
            Label(f"A1: {state.a1}")
            Label(f"B1: {state.b1}")
            with Table(columnHeader=["Col 1", "Col 2", "Col 3"], rowHeader=["Row 1", "Row 2", "Row 3"]):
                with TableNode():
                    TableNode(state.a1).set(self.on_set, 0, 0)
                    TableNode("A2").click(self.on_click, "A2").dblclick(self.on_dblclick, "A2")
                    TableNode("A3").click(self.on_click, "A3").dblclick(self.on_dblclick, "A3")
                with TableNode():
                    TableNode(state("b1"))
                    TableNode("B2").click(self.on_click, "B2").dblclick(self.on_dblclick, "B2")
                    TableNode("B3").click(self.on_click, "B3").dblclick(self.on_dblclick, "B3")

    def on_set(self, data, *args):
        print("on_set", data, args)
        state.a1 = data

    def on_click(self, e, data):
        print("on_click", data)

    def on_dblclick(self, e, data):
        print("on_dblclick", data)