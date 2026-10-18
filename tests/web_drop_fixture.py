from pathlib import Path
from PUI.web import Application, Window, VBox, Label, State


class App(Application):
    def setup(self):
        self.state = State()
        self.state.value = 'Waiting'

    def content(self):
        with Window():
            with VBox():
                Label('Accept').drop(self.accept, extensions=('.txt',))
                Label('Reject').drop(self.reject)
                Label('Implicit').drop(lambda e: None)
                Label(self.state.value)

    def accept(self, event):
        self.state.value = '|'.join(Path(f.path).read_text() for f in event.files) or event.text or '|'.join(event.urls)
        event.accept()

    def reject(self, event):
        event.reject('Rejected by application')
