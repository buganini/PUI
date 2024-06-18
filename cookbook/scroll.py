from .config import *

state = State()
state.var = 100

@PUI
def ScrollExample():
    def more():
        state.var += 1
    def less():
        state.var -= 1
    with VBox():
        with HBox():
            Button("-").click(less)
            Label(f"{state.var}")
            Button("+").click(more)
        with Scroll().layout(weight=1).scrollY(Scroll.END):
            with VBox():
                for i in range(state.var):
                    Label(f"Row {i+1}")
