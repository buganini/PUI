from .config import *

class ModalExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.modal_open = False

    def content(self):
        with VBox():
            Label(f"State: {self.state.modal_open}")
            Button("Open Modal").click(self.open)
            Spacer()
            with (Modal(self.state("modal_open"), "Modal Window")
                  .open(self.on_open)
                  .close(self.on_close)):
                Button("Close Modal").click(self.close)

    def open(self):
        self.state.modal_open = True

    def close(self):
        self.state.modal_open = False

    def on_open(self):
        print("on_open")

    def on_close(self):
        print("on_close")
