from .config import *

state = State()
state.text = 1.23
state.editing = ""

class TextFieldExample(PUIView):
    def clear_state(self, event):
        state.text = ""

    def set_something(self, event):
        state.text = "something"

    def content(self):
        with VBox():
            with HBox():
                Button("Clear").click(self.clear_state)
                Button("Set something").click(self.set_something)
                Spacer()

            Label("State Model")
            Label("State:" + str(state.text))
            (TextField(state("text"), placeholder="Enter text")
                .input(lambda e: print("input", e))
                .change(lambda e: print("change", e)))

            Label("Editing Buffer Model")
            Label("State:" + str(state.text))
            Label("Editing:" + str(state.editing))
            TextField(state("text"), state("editing"))

            Spacer()
