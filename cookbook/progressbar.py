from .config import *

state = State()
state.progress = 50

@PUI
def ProgressBarExample():
    with VBox():
        with HBox():
            def reduce(e, x):
                state.progress -= x
            def add(e, x):
                state.progress += x
            Button("-5").click(reduce, 5)
            Label(f"{state.progress}")
            Button("+5").click(add, 5)

        ProgressBar(progress=state.progress, maximum=100)

        Spacer()
