from .config import *


class AdaptiveLayoutExample(PUIView):
    def setup(self):
        self.form = State()
        self.form.name = 'Ada'

    def content(self):
        # Textual sizes are terminal cells, rather than logical pixels.
        breakpoint = 60 if backend == 'textual' else 600
        with VBox().layout(weight=1).tlayout(weight=1, padding=1) as container:
            size = (container.tsize() if backend == 'textual' else container.size()).value
            Label('Container size: waiting for layout' if size is None else
                  f'Container size: {size[0]:.0f} × {size[1]:.0f}')
            Label(f'Resize the window: breakpoint = {breakpoint}')
            with VBox().id('compact').visible(maxWidth=600, tMaxWidth=60):
                Label('Compact layout').tstyle(color=0x55CC99, fontWeight='bold')
                Label('Name')
                TextField(self.form('name'))
                Label('The two layouts share the same input state.')
            with HBox().id('wide').visible(minWidth=600, tMinWidth=60):
                Label('Wide layout').tstyle(color=0x55CC99, fontWeight='bold')
                Label('Name')
                TextField(self.form('name'))
                Label('Shared input state')
            Label('HVBox: one input, retained while the direction changes')
            with HVBox(minWidth=600, tMinWidth=60):
                Label('Name')
                TextField(self.form('name'))
                Button('Save')
            Label('VHBox: vertical when the parent is tall enough')
            with VHBox(minHeight=500, tMinHeight=35):
                Label('First')
                Label('Second')
                Label('Third')
            Spacer()
