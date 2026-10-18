from .config import *


state = State()
state.a1 = "A1"
state.b1 = "B1"
state.sides = 4
state.direction = "CW"
state.price = ""

class TableExample(PUIView):
    def content(self):
        with VBox():
            Label(f"A1: {state.a1}")
            Label(f"B1: {state.b1}")
            Label(f"Sides: {state.sides}")
            Label(f"Direction: {state.direction}")
            Label(f"Price: ${state.price} USD")
            with Table(
                columnHeader=["Col 1", "Col 2", "Col 3", "Choice"],
                rowHeader=["Row 1", "Row 2", "Row 3"],
            ):
                with TableNode():
                    TableNode(
                        state("a1"),
                        display=f"A1: {state.a1}",
                        prefix="editable: ",
                    )
                    TableNode("A2", prefix="editable: ").set(self.on_set, 0, 1)
                    TableNode("A3").click(self.on_click, "A3").dblclick(self.on_dblclick, "A3")
                    TableNode(
                        state("sides"),
                        choices=(3, 4, 5, 6, 8),
                        prefix="editable: ",
                    )
                with TableNode():
                    TableNode(state("b1"), prefix="editable: ")
                    TableNode("B2").click(self.on_click, "B2").dblclick(self.on_dblclick, "B2")
                    TableNode("B3").click(self.on_click, "B3").dblclick(self.on_dblclick, "B3")
                    TableNode(
                        state("direction"),
                        prefix="editable: ",
                        choices={
                            "CW": "Clockwise",
                            "CCW": "Counterclockwise",
                        },
                    )
                with TableNode():
                    TableNode(state("price"), prefix="editable: Price: $", suffix=" USD",
                              placeholder="Enter price")
                    TableNode("")
                    TableNode("")
                    TableNode("")

    def on_set(self, data, *args):
        print("on_set", data, args)
        state.a1 = data

    def on_click(self, e, data):
        print("on_click", data)

    def on_dblclick(self, e, data):
        print("on_dblclick", data)
