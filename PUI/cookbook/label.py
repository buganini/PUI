from .config import *

class LabelExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.show = True

    def content(self):
        with VBox():
            Checkbox("Show greeting", self.state("show"))
            Label("Hello World").visible(self.state.show)
            Label("Color").style(
                fontSize=20, color=0xD3B98B, bgColor=0x1C2A30,
            ).tStyle(color=0xD3B98B, bgColor=0x1C2A30)
            Label(text="No <b>HTML</b>")
            Spacer()
