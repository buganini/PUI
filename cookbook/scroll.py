from .config import *

state = State()
state.var = 100

@PUI
def ScrollExample():
    def more(e):
        state.var += 1
    def less(e):
        state.var -= 1
    with VBox().layout(weight=1):
        with HBox():
            Button("-").click(less)
            Label(f"{state.var}")
            Button("+").click(more)
        with Scroll().layout(weight=1).scrollY(Scroll.END):
            with VBox():
                for i in range(state.var):
                    Label(f"Row {i+1}")
