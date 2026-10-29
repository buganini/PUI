from PUI.web import Application, Window, Button, Label, State, SaveFile


class App(Application):
    def setup(self):
        self.state = State()
        self.state.value = 'idle'

    def content(self):
        with Window():
            Button('Save File').click(self.save)
            Label(self.state.value)

    def save(self, event):
        self.state.value = str(SaveFile(default='report.txt', title='Save report'))
