from .config import *

class CheckboxExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.value1 = True
        self.state.value2 = True
        self.state.list_value = []
        self.state.dict_value = {}

    def content(self):
        with VBox():
            Label(f"Model value 1: {self.state.value1}")
            Label(f"Model value 2: {self.state.value2}")

            Checkbox("checkbox 1-1", self.state("value1"))
            Checkbox(text="checkbox 1-2", model=self.state("value1"))
            Checkbox("checkbox 2", self.state("value2"))

            Divider()

            Label(f"List value: {self.state.list_value}")
            Checkbox("checkbox 3", self.state("list_value"), "value 3")
            Checkbox("checkbox 4", self.state("list_value"), "value 4")
            Checkbox("checkbox 5", self.state("list_value"), "value 5")

            Divider()

            Label(f"Dict value: {self.state.dict_value}")
            Checkbox("checkbox 6", self.state("dict_value"), "value 6")
            Checkbox("checkbox 7", self.state("dict_value"), "value 7")
            Checkbox("checkbox 8", self.state("dict_value"), "value 8")

            Spacer()
