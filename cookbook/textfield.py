from PUI.PySide6 import *

state = State()
state.text = "test"

@PUI
def TextFieldExample():
    with VBox():
        Label(state.text)
        TextField(state("text"))
        Spacer()