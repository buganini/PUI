from .config import *

class DialogExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.directory = None
        self.state.file = None
        self.state.files = None

    def content(self):
        with VBox():
            Label(f"Directory: {type(self.state.directory)}: {self.state.directory}")
            Button("Open Directory").click(OpenDirectory, self.state("directory"))

            Label(f"File: {type(self.state.file)}: {self.state.file}")
            Button("Open File").click(OpenFile, self.state("file"))
            Button("Save File (default to model)").click(SaveFile, self.state("file"))

            Label(f"Files: {type(self.state.files)}: {self.state.files}")
            Button("Open Files").click(OpenFiles, self.state("files"))

            Spacer()
