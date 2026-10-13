from .config import *


class ViewsEditor(PUIView):
    def __init__(self):
        super().__init__()
        self.text = DummyBinding('This text survives switching views.')

    def content(self):
        with VBox():
            Label('Editor')
            TextField(self.text)


class ViewsExample(PUIView):
    def __init__(self):
        super().__init__()
        self.selection = DummyBinding('editor')

    def choose(self, event, key):
        self.container.select(key)

    def content(self):
        with VBox():
            with HBox():
                Button('Editor').click(self.choose, 'editor')
                Button('Settings').click(self.choose, 'settings')
                Button('Clear').click(self.choose, None)
            with Views(self.selection).layout(weight=1) as self.container:
                ViewsEditor().id('editor')
                with VBox().id('settings'):
                    Label('Settings')
                    Label('Return to Editor to see the retained text.')
