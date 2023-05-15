from .config import *

state = State()
state.value = "A"

@PUI
def ButtonExample():
    with HBox():
        Label(state.value)

        def set_value(x):
            state.value = x

        Button("A").click(set_value, "A")
        Button("B").click(set_value, "B")

        Spacer()
