from .config import *

class ModalExample(PUIView):
    class Modal(PUIView):
        def __init__(self, state):
            super().__init__()
            self.state = state

        def content(self):
            with Modal("Modal Window"):
                Button("Close Modal").click(self.close)

        def close(self):
            self.state.model_open = False

    def setup(self):
        self.state = State()
        self.state.model_open = False

    def content(self):
        with VBox():
            Button("Open Modal").click(self.open)
            Spacer()
            if self.state.model_open:
                ModalExample.Modal(self.state)

    def open(self):
        self.state.model_open = True