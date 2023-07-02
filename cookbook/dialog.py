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
            Button("Open Directory").click(self.do_open_dir)

            Label(f"File: {type(self.state.file)}: {self.state.file}")
            Button("Open File").click(self.do_open_file)
            Button("Save File (default to model)").click(self.do_save_file)

            Label(f"Files: {type(self.state.files)}: {self.state.files}")
            Button("Open Files").click(self.do_open_files)

            Label(f"Information:")
            Button("Information").click(Information, "info title", "info message")

            Label(f"Warning:")
            Button("Warning").click(Warning, "warning title", "warning message")

            Label(f"Critical:")
            Button("Critical").click(Critical, "critical title", "critical message")

            Label(f"Confirm: {self.state.confirm}")
            Button("Confirm").click(self.do_confirm)

            Label(f"Prompt: {self.state.prompt}")
            Button("Prompt").click(self.do_prompt)

            Spacer()

    def do_open_dir(self):
        self.state.directory = OpenDirectory()

    def do_open_file(self):
        self.state.file = OpenFile()

    def do_save_file(self):
        self.state.file = SaveFile(self.state.file)

    def do_open_files(self):
        self.state.files = OpenFiles()

    def do_confirm(self):
        self.state.confirm = Confirm("confirm title", "confirm message")

    def do_prompt(self):
        self.state.prompt = Prompt("default", "prompt title", "prompt message")