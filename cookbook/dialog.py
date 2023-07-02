from .config import *

class DialogExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.directory = None
        self.state.file = None
        self.state.files = None
        self.state.confirm = None
        self.state.prompt = None

    def content(self):
        with VBox():
            Label(f"Directory: {type(self.state.directory)}: {self.state.directory}")
            Button("Open Directory").click(OpenDirectory, self.state("directory"))

            Label(f"File: {type(self.state.file)}: {self.state.file}")
            Button("Open File").click(OpenFile, self.state("file"))
            Button("Save File (default to model)").click(SaveFile, self.state("file"))

            Label(f"Files: {type(self.state.files)}: {self.state.files}")
            Button("Open Files").click(OpenFiles, self.state("files"))

            Label(f"Information:")
            Button("Information").click(Information, "info title", "info message")

            Label(f"Warning:")
            Button("Warning").click(Warning, "warning title", "warning message")

            Label(f"Critical:")
            Button("Critical").click(Critical, "critical title", "critical message")

            Label(f"Confirm: {self.state.confirm}")
            Button("Confirm").click(Confirm, self.state("confirm"), "confirm title", "confirm message")

            Label(f"Prompt: {self.state.prompt}")
            Button("Prompt").click(Prompt, self.state("prompt"), "prompt title", "prompt message")

            Spacer()
