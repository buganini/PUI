from .config import *

class ModalExample(PUIView):
    class Modal(PUIView):
        def __init__(self, open):
            super().__init__()
            self.open = open

        def content(self):
            with Modal("Modal Window"):
                Button("Close Modal").click(self.close)

        def close(self):
            self.open.value = False

    def setup(self):
        self.state = State()
        self.state.model_open = False

    def content(self):
        with VBox():
            Button("Open Modal").click(self.open)
            Spacer()
            if self.state.model_open:
                ModalExample.Modal(self.state("model_open"))

    def open(self):
        self.state.model_open = True