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
                Button("Disabled", disabled=True).click(self.set_value, "Disabled")

                Button(text="Styled").style(
                    fontSize=20, color=0x244B5A, bgColor=0xFFF7E6,
                ).tStyle(color=0x244B5A, bgColor=0xFFF7E6, fontWeight="bold")

                Spacer()
            Spacer()
