from .config import *

state = State()
state.var = 100

class ScrollExample(PUIView):
    def more(self, event):
        state.var += 1

    def less(self, event):
        state.var -= 1

    def content(self):
        with VBox().id("result-scroller-container").debug():
            with HBox().debug():
                Button("-").click(self.less)
                Label(f"{state.var}")
                Button("+").click(self.more)
            with Scroll().id("scroller").scrollY(Scroll.END).debug():
                with VBox().id("scrolled-content").debug():
                    for i in range(state.var):
                        Label(f"Row {i+1}")
