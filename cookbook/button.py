from .config import *

state = State()
state.value = "A"

class ButtonExample(PUIView):
    def set_value(self, event, value):
        state.value = value

    def content(self):
        with VBox():
            with HBox():
                Label(state.value)

                Button("A").click(self.set_value, "A")
                Button(text="B").click(self.set_value, "B")

                Button(text="Styled").style(fontSize=20, color=0xFF0000)

                Spacer()
            Spacer()
