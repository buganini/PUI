from .config import *

state = State()
state.value = None

class RadioButtonExample(PUIView):
    def select_disabled(self, event):
        state.value = "disabled"

    def content(self):
        with VBox():
            Label(f"Model value: {state.value}")

            RadioButton("A", "a", state("value"))
            RadioButton(text="B", value="b", model=state("value"))
            RadioButton("Disabled", "disabled", state("value"), enabled=False)
            Button("Select disabled option").click(self.select_disabled)

            Spacer()
