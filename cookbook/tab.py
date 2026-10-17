from .config import *

class TabExample(PUIView):
    def setup(self):
        self.optional_state = State()
        self.optional_state.selection = 'first'

    def choose(self, event, key):
        ref('cookbook.tabs').select(key)

    def choose_state(self, event, key):
        self.optional_state.selection = key

    def pages(self):
        with Tab('Tab 1').id('first'):
            Label('Selected by explicit ID: first')
        with Tab('Tab 2'):
            Label('Selected by fallback ID: Tab 2')

    def content(self):
        with VBox().layout(weight=1):
            Label('Select with .select(): internal model')
            with HBox():
                Button('Tab 1').click(self.choose, 'first')
                Button('Tab 2').click(self.choose, 'Tab 2')
            with Tabs().layout(weight=1).ref('cookbook.tabs'):
                self.pages()

            Label(f'Select by state: {self.optional_state.selection!r}')
            with HBox():
                Button('Tab 1').click(self.choose_state, 'first')
                Button('Tab 2').click(self.choose_state, 'Tab 2')
            with Tabs(model=self.optional_state('selection')).layout(weight=1):
                self.pages()


if __name__ == '__main__':
    class App(Application):
        def content(self):
            with Window():
                TabExample()
    App().run()
