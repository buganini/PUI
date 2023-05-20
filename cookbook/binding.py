from .config import *

class BindingExample(PUIView):
    def setup(self):
        print("setup()")
        self.state = State()
        self.state.var = None

        self.value_holder = "test"

        self.state("var").change(self.on_changed_func)
        self.state("var").bind(self.getter_func, self.setter_func)

    def content(self):
        with VBox():
            Label(f"var: {self.state.var}")
            TextField(self.state("var"))
            Label("Check log messages in the console")
            Spacer()

    def getter_func(self):
        print("getter_func")
        return self.value_holder

    def setter_func(self, value):
        print("setter_func", value)
        self.value_holder = value

    def on_changed_func(self, value):
        print("on_changed_func", value)
