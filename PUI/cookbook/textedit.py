from .config import *


class TextEditExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.text = ''
        self.state.draft = ''
        self.state.readonly = False
        self.state.status = 'Enter inserts a newline; Tab or another control commits.'

    def on_input(self, event):
        self.state.status = f'Editing {len(event.value)} characters'

    def on_change(self, event):
        self.state.status = f'Committed {len(event.value)} characters'

    def content(self):
        with VBox():
            Label('Multiline plain text editor')
            Checkbox('Read only', self.state('readonly'))
            TextEdit(self.state('text'), self.state('draft'), placeholder='Type several lines…',
                     readonly=self.state.readonly).input(self.on_input).change(self.on_change).layout(weight=1)
            Label(self.state.status)
            Label(f'Committed: {self.state.text!r}')
            Label(f'Draft: {self.state.draft!r}')
