from .config import *

class LabelExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.show = True

    def content(self):
        with VBox():
            Checkbox("Show greeting", self.state("show"))
            Label("Hello World").visible(self.state.show)
            Label("Big Yellow").style(fontSize=20, color=0xFFFF00, bgColor=0xFF0000).tStyle(color=0xFFFF00, bgColor=0xFF0000)
            Label(text="No <b>HTML</b>")
            Spacer()
