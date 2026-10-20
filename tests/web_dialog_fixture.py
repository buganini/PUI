from PUI.web import Application, Window, Button, Label, State, Confirm, Prompt, Information


class App(Application):
    def setup(self):
        self.state = State()
        self.state.value = 'idle'

    def content(self):
        with Window():
            Button('Ask').click(self.ask)
            Button('Other').click(lambda event: setattr(self.state, 'value', 'other'))
            Label(self.state.value)

    def ask(self, event):
        try:
            answer = Confirm('Continue?', title='Test')
            text = Prompt('Text?', default='initial')
            Information('Finished')
            self.state.value = repr((answer, text))
        except ConnectionError:
            self.state.value = 'disconnected'
