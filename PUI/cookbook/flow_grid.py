from .config import *


class FlowGridExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.expandChildren = False

    def content(self):
        expandChildren = self.state('expandChildren')
        with VBox().layout(weight=1):
            Label('Flow Grid: items auto-flow into columns.')
            Checkbox('expandChildren', expandChildren)
            with Scroll().layout(weight=1):
                with Grid().columns(3, expandChildren=expandChildren.value).wideColumns(500, 5, expandChildren=expandChildren.value):
                    with VBox().style(bgColor=0x4A90D9).layout(padding=8, minHeight=30).grid(columnspan=5):
                        Label('Header').style(color=0xFFFFFF)
                    for i in range(1, 21):
                        with VBox().style(bgColor=0xE88A2A).layout(padding=8, minHeight=30):
                            Label(f'Item {i}').style(color=0x000000)
