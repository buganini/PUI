from .config import *

state = State()
state.text = "test"
state.editing = ""

@PUI
def TextFieldExample():
    with VBox():
        Label("State")
        Label(state.text)
        TextField(state("text"))
        Label("Editing Buffer")
        Label(state.editing)
        TextField(state("text"), state("editing"))
        Spacer()