from .config import *

state = State()
state.value = True

@PUI
def CheckboxExample():
    with VBox():
        Label(f"Model value: {state.value}")

        Checkbox("checkbox", state("value"))

        Spacer()
