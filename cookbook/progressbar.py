from .config import *

state = State()
state.progress = 50

class ProgressBarExample(PUIView):
    def reduce(self, event, amount):
        state.progress -= amount

    def add(self, event, amount):
        state.progress += amount

    def content(self):
        with VBox():
            with HBox():
                Button("-5").click(self.reduce, 5)
                Label(f"{state.progress}")
                Button("+5").click(self.add, 5)

            ProgressBar(progress=state.progress, maximum=100)

            Spacer()
