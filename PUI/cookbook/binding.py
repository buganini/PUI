from .config import *
from collections import deque


class BindingExample(PUIView):
    def setup(self):
        self.log_lines = deque(maxlen=100)
        self.state = State()
        self.state.var = None
        self.state.logs = ""
        self.state.choice = "Value 1"
        self.log("setup()")

        self.value_holder = "test"

        self.state("var").change(self.on_changed_func)
        self.state("var").bind(self.getter_func, self.setter_func)

    def content(self):
        with VBox().layout(weight=1):
            Label("Shared binding")
            Label(f"Selected value: {self.state.choice}")
            # Different controls read and write the same State attribute.
            with ComboBox(editable=False, text_model=self.state("choice")):
                ComboBoxItem("Item 1", "Value 1")
                ComboBoxItem("Item 2", "Value 2")
                ComboBoxItem("Item 3", "Value 3")
            RadioButton("Value 1", "Value 1", self.state("choice"))
            RadioButton("Value 2", "Value 2", self.state("choice"))
            RadioButton("Value 3", "Value 3", self.state("choice"))

            Divider()
            Label("Custom getter / setter")
            Label(f"var: {self.state.var}")
            TextField(self.state("var"))
            Label("Binding log (latest 100 messages)")
            with Scroll().layout(weight=1):
                Text(self.state.logs)

    def log(self, message):
        self.log_lines.append(message)
        self.state.logs = "\n".join(self.log_lines)

    def getter_func(self):
        self.log("getter_func")
        return self.value_holder

    def setter_func(self, value):
        self.log(f"setter_func {value}")
        self.value_holder = value

    def on_changed_func(self, value):
        self.log(f"on_changed_func {value}")
