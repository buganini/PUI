from .config import *

state = State()
state.index = -1
state.text = ""

@PUI
def ComboboxExample():
    with VBox():
        Label(f"Index: {state.index}")
        Label(f"Text: {state.text}")

        with HBox():
            Label("Readonly")
            with ComboBox(editable=False, text_model=state("text")):
                ComboBoxItem("Item 1", "Value 1")
                ComboBoxItem("Item 2", "Value 2")
                ComboBoxItem("Item 3", "Value 3")
            Spacer()

        with HBox():
            Label("Editable")
            with ComboBox(editable=True, index_model=state("index"), text_model=state("text")):
                ComboBoxItem("Item 1")
                ComboBoxItem("Item 2")
                ComboBoxItem("Item 3", "Value 3")
            Spacer()

        Spacer()
