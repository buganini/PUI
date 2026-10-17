"""The worker must populate Options before importing this application module."""
import json
import PUI
from PUI.web import Application, Window, Label, Button, TextField, State

IMPORTED_OPTIONS = dict(PUI.Options)


class App(Application):
    def setup(self):
        self.initial = dict(PUI.Options)
        self.state = State()
        self.state.count = int(PUI.Options.get('example.count', '0'))

    def increment(self, event):
        self.state.count += 1

    def content(self):
        with Window('Options test'):
            Label('import=' + json.dumps(IMPORTED_OPTIONS, sort_keys=True))
            Label('setup=' + json.dumps(self.initial, sort_keys=True))
            Label('current=' + json.dumps(PUI.Options, sort_keys=True))
            TextField(self.state('count').ref('example.count'))
            Button('Increment').click(self.increment)
