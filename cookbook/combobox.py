from .config import *

state = State()
state.index = -1
state.text = ""

@PUI
def ComboboxExample():
    with VBox():
        Label(f"Index: {state.index}")
        Label(f"Text: {state.text}")
        with Combobox(editable=True, index_model=state("index"), text_model=state("text")):
            ComboboxItem("Item 1")
            ComboboxItem("Item 2")
            ComboboxItem("Item 3")

        Spacer()
