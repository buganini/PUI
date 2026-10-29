from .config import *

class DialogExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.directory = None
        self.state.file = None
        self.state.save_path = None
        self.state.files = None
        self.state.confirm = None
        self.state.prompt = None

    def content(self):
        with Scroll().layout(weight=1), VBox():
            Label(f"Directory: {type(self.state.directory)}: {self.state.directory}")
            Button("Open Directory").click(self.do_open_dir)

            Divider()
            Label(f"File: {type(self.state.file)}: {self.state.file}")
            with HBox():
                Button("Open File").click(self.do_open_file)
                Button("Open File with Filter (*.txt)").click(self.do_open_file_filter)

            Divider()
            Label(f"Files: {type(self.state.files)}: {self.state.files}")
            Button("Open Files").click(self.do_open_files)

            Divider()
            Label(f"Save path: {self.state.save_path}")
            Button("Save File").click(self.do_save_file)

            Divider()
            Label(f"Information:")
            Button("Information").click(lambda event: Information("info message", title="info title"))

            Divider()
            Label(f"Warning:")
            Button("Warning").click(lambda event: Warning("warning message", title="warning title"))

            Divider()
            Label(f"Critical:")
            Button("Critical").click(lambda event: Critical("critical message", title="critical title"))

            Divider()
            Label(f"Confirm: {self.state.confirm}")
            Button("Confirm").click(self.do_confirm)

            Divider()
            Label(f"Prompt: {self.state.prompt}")
            Button("Prompt").click(self.do_prompt)

            Spacer()

    def do_open_dir(self, e):
        self.state.directory = OpenDirectory()

    def do_open_file_filter(self, e):
        self.state.file = OpenFile(types={"Text files": ["txt"]})

    def do_open_file(self, e):
        self.state.file = OpenFile()

    def do_save_file(self, e):
        self.state.save_path = SaveFile(self.state.save_path)
        if backend == 'pyodide' and self.state.save_path is not None:
            from pathlib import Path
            Path(self.state.save_path).write_text('PUI cookbook download\n', encoding='utf-8')

    def do_open_files(self, e):
        self.state.files = OpenFiles()

    def do_confirm(self, e):
        self.state.confirm = Confirm("confirm message", title="confirm title")

    def do_prompt(self, e):
        self.state.prompt = Prompt("prompt message", title="prompt title", default="default")
