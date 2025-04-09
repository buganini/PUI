from .config import *

state = State()
state.text = 1.23
state.editing = ""

def clear_state(e):
    state.text = ""

def set_something(e):
    state.text = "something"

@PUI
def TextFieldExample():
    with VBox():
        with HBox():
            Button("Clear").click(clear_state)
            Button("Set something").click(set_something)
            Spacer()

        Label("State Model")
        Label("State:" + str(state.text))
        (TextField(state("text"))
            .input(lambda e: print("input", e))
            .change(lambda e: print("change", e)))

        Label("Editing Buffer Model")
        Label("State:" + str(state.text))
        Label("Editing:" + str(state.editing))
        TextField(state("text"), state("editing"))

        Spacer()