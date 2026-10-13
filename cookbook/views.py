from .config import *


class ViewsExample(PUIView):
    class ViewsEditor(PUIView):
        def setup(self):
            self.state = State()
            self.state.text = 'This text survives switching views.'

        def content(self):
            with VBox():
                Label('Editor')
                TextField(self.state('text'))
                Spacer()

    def setup(self):
        self.optional_state = State()
        self.optional_state.selection = 'editor'

    def choose(self, event, key):
        self.container.select(key)

    def choose_state(self, event, key):
        self.optional_state.selection = key

    def pages(self):
        self.ViewsEditor().id('editor')
        with VBox().id('settings'):
            Label('Settings')
            Label('Return to Editor to see the retained text.')
            Spacer()

    def content(self):
        with VBox().layout(weight=1):
            Label('Select with .select(): internal model, initially empty')
            with HBox():
                Button('Editor').click(self.choose, 'editor')
                Button('Settings').click(self.choose, 'settings')
                Button('Clear').click(self.choose, None)
            with Views().layout(weight=1) as self.container:
                self.pages()

            Label(f'Select by state: {self.optional_state.selection!r}')
            with HBox():
                Button('Editor').click(self.choose_state, 'editor')
                Button('Settings').click(self.choose_state, 'settings')
                Button('Clear').click(self.choose_state, None)
            with Views(model=self.optional_state('selection')).layout(weight=1):
                self.pages()
