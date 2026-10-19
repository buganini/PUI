from .config import *


class AdaptiveLayoutExample(PUIView):
    def setup(self):
        self.form = State()
        self.form.name = 'Ada'

    def content(self):
        # Textual sizes are terminal cells, rather than logical pixels.
        breakpoint = 60 if backend == 'textual' else 600
        with VBox().layout(weight=1) as container:
            size = container.size().value
            Label('Container size: waiting for layout' if size is None else
                  f'Container size: {size[0]:.0f} × {size[1]:.0f}')
            Label(f'Resize the window: breakpoint = {breakpoint}')
            with VBox().id('compact').visible(max_width=breakpoint):
                Label('Compact layout')
                Label('Name')
                TextField(self.form('name'))
                Label('The two layouts share the same input state.')
            with HBox().id('wide').visible(min_width=breakpoint):
                Label('Wide layout')
                Label('Name')
                TextField(self.form('name'))
                Label('Shared input state')
            Spacer()
