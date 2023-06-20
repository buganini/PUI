from .config import *

class DialogExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.model = None

    def content(self):
        with VBox():
            Label(f"Model: {type(self.state.model)}: {self.state.model}")
            Button("Open File").click(self.openfile)
            Button("Open Files").click(self.openfiles)
            Button("Save File (default to model)").click(self.savefile)
            Spacer()

    def openfile(self):
        OpenFile(self.state("model"))

    def openfiles(self):
        OpenFiles(self.state("model"))

    def savefile(self):
        SaveFile(self.state("model"))
