from .config import *

state = State()
state.value = None

@PUI
def RadioButtonExample():
    with VBox():
        Label(f"Model value: {state.value}")

        RadioButton("A", "a", state("value"))
        RadioButton("B", "b", state("value"))

        Spacer()
