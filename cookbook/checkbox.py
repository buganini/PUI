from .config import *

state = State()
state.value1 = True
state.value2 = True

@PUI
def CheckboxExample():
    with VBox():
        Label(f"Model value 1: {state.value1}")
        Label(f"Model value 2: {state.value2}")

        Checkbox("checkbox 1-1", state("value1"))
        Checkbox(text="checkbox 1-2", model=state("value1"))
        Checkbox("checkbox 2", state("value2"))

        Spacer()
