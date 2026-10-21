from .config import *


class AdaptiveLayoutExample(PUIView):
    def setup(self):
        self.form = State()
        self.form.name = 'Ada'
        self.form.inverse_h = False
        self.form.inverse_v = False

    def content(self):
        # Textual sizes are terminal cells, rather than logical pixels.
        breakpoint = 60 if backend == 'textual' else 600
        with VBox().layout(weight=1).tLayout(padding=1) as container:
            size = (container.tsize() if backend == 'textual' else container.size()).value
            Label('Container size: waiting for layout' if size is None else
                  f'Container size: {size[0]:.0f} × {size[1]:.0f}')
            Label(f'Resize the window: breakpoint = {breakpoint}')
            with HBox():
                Checkbox('Reverse horizontal', self.form('inverse_h'))
                Checkbox('Reverse vertical', self.form('inverse_v'))
            with VBox().id('compact').visible(maxWidth=600, tMaxWidth=60):
                Label('Compact layout').tStyle(color=0x55CC99, fontWeight='bold')
                Label('Name')
                TextField(self.form('name'))
                Label('The two layouts share the same input state.')
            with HBox().id('wide').visible(minWidth=600, tMinWidth=60):
                Label('Wide layout').tStyle(color=0x55CC99, fontWeight='bold')
                Label('Name')
                TextField(self.form('name'))
                Label('Shared input state')
            Divider()
            Label('Wide layout/style overrides').style(color=0x777777, fontSize=12).wideStyle(
                600, color=0x228855, fontSize=18,
            ).tStyle(color=0x777777).tWideStyle(60, color=0x55CC99, fontWeight='bold').layout(
                padding=2,
            ).wideLayout(600, padding=12).tLayout(padding=0).tWideLayout(60, padding=1)
            Divider()
            Label('HVBox: one input, retained while the direction changes')
            with HVBox(minWidth=600, tMinWidth=60,
                       inverseH=self.form.inverse_h, inverseV=self.form.inverse_v):
                Label('Name')
                TextField(self.form('name'))
                Button('Button')
            Divider()
            Label('VHBox: vertical when the parent is tall enough')
            with VHBox(minHeight=500, tMinHeight=35,
                       inverseH=self.form.inverse_h, inverseV=self.form.inverse_v):
                Label('First')
                Label('Second')
                Label('Third')
            Spacer()
