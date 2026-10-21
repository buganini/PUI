from .config import *
from pathlib import Path


class DropExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.result = "Drop .txt/.json files, directories (native backends), text, or URLs"
        self.state.reject = False
        self.state.text_content = ""

    def content(self):
        with VBox():
            Label("DROP HERE").style(fontSize=36, color=0xD3B98B, bgColor=0x1C2A30).drop(
                self.handle_drop, extensions=(".txt", ".json", "/"),
            )
            Checkbox("Reject this drop", self.state("reject"))
            Label(self.state.result)
            Label(self.state.text_content)
            Spacer()

    def handle_drop(self, event):
        if self.state.reject:
            event.reject("Rejected by the example")
            return
        lines = ["Action: " + event.action]
        contents = []
        for file in event.files:
            # Temporary paths remain available until the session ends;
            # applications may copy or delete their temporary files earlier.
            if Path(file.path).is_dir():
                lines.append(f"{file.name}: directory ({file.path})")
                continue
            lines.append(f"{file.name}: {Path(file.path).stat().st_size} bytes (temporary={file.temporary})")
            if file.name.lower().endswith(".txt"):
                text = Path(file.path).read_text(encoding="utf-8", errors="replace")
                contents.append(f"{file.name}\n{text}")
        if event.text:
            lines.append(event.text)
        lines.extend(event.urls)
        self.state.result = "\n".join(lines)
        self.state.text_content = "\n\n".join(contents)
        event.accept()  # Required: returning without accept() rejects the drop.
