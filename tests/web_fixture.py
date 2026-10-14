"""Importable worker application used by the real gateway tests."""
import os
from PUI.web import Application, Window, VBox, Label, Button, TextField, State


class App(Application):
    def setup(self):
        self.state = State()
        self.state.count = 0
        self.state.text = 1.23

    def increment(self, event):
        self.state.count += 1

    def content(self):
        with Window('Web test'):
            with VBox():
                Label('pid=' + str(os.getpid()))
                Label('count=' + str(self.state.count))
                Button('Increment').click(self.increment)
                TextField(self.state('text'))
