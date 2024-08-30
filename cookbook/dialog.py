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
            Button("Information").click(lambda event: Information("info message", title="info title"))

            Label(f"Warning:")
            Button("Warning").click(lambda event: Warning("warning message", title="warning title"))

            Label(f"Critical:")
            Button("Critical").click(lambda event: Critical("critical message", title="critical title"))

            Label(f"Confirm: {self.state.confirm}")
            Button("Confirm").click(self.do_confirm)

            Label(f"Prompt: {self.state.prompt}")
            Button("Prompt").click(self.do_prompt)

            Spacer()

    def do_open_dir(self, e):
        self.state.directory = OpenDirectory()

    def do_open_file(self, e):
        self.state.file = OpenFile()

    def do_save_file(self, e):
        self.state.file = SaveFile(self.state.file)

    def do_open_files(self, e):
        self.state.files = OpenFiles()

    def do_confirm(self, e):
        self.state.confirm = Confirm("confirm message", title="confirm title")

    def do_prompt(self, e):
        self.state.prompt = Prompt("prompt message", title="prompt title", default="default")
