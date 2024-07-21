from .config import *

state = State()
state.value = "A"

@PUI
def ButtonExample():
    with VBox():
        with HBox():
            Label(state.value)

            def set_value(e, x):
                state.value = x

            Button("A").click(set_value, "A")
            Button(text="B").click(set_value, "B")

            Spacer()
        Spacer()
