from PUI.web import Application, Window, VBox, Button, Label, State, OpenDirectory, OpenFile, OpenFiles

class App(Application):
    def setup(self):
        self.state = State()
        self.state.result = 'idle'
    def content(self):
        with Window(), VBox():
            Button('Open Directory').click(lambda e: self.choose(OpenDirectory))
            Button('Open File').click(lambda e: self.choose(OpenFile))
            Button('Open Files').click(lambda e: self.choose(OpenFiles))
            Label(str(self.state.result))
    def choose(self, helper):
        self.state.result = helper()
