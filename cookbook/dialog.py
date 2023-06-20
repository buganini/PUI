from .config import *

class DialogExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.model = None

    def content(self):
        with VBox():
            Label(f"Model: {self.state.model}")
            Button("Select File").click(self.selectfile)
            Spacer()

    def selectfile(self):
        SelectFile(self.state("model"))
