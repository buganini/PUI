from .config import *

class DialogExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.file = None
        self.state.files = None

    def content(self):
        with VBox():
            Label(f"File: {type(self.state.file)}: {self.state.file}")
            Button("Open File").click(self.openfile)
            Button("Save File (default to model)").click(self.savefile)

            Label(f"Files: {type(self.state.files)}: {self.state.files}")
            Button("Open Files").click(self.openfiles)

            Spacer()

    def openfile(self):
        OpenFile(self.state("file"))

    def openfiles(self):
        OpenFiles(self.state("files"))

    def savefile(self):
        SaveFile(self.state("file"))
