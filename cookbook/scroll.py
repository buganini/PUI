from .config import *

state = State()
state.var = 100

@PUI
def ScrollExample():
    def more(e):
        state.var += 1
    def less(e):
        state.var -= 1
    with VBox().id("result-scroller-container").layout(weight=1).debug():
        with HBox().debug():
            Button("-").click(less)
            Label(f"{state.var}")
            Button("+").click(more)
        with Scroll().id("scroller").scrollY(Scroll.END).debug():
            with VBox().id("scrolled-content").debug():
                for i in range(state.var):
                    Label(f"Row {i+1}")
