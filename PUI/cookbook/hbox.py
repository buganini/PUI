from .config import *

class HBoxExample(PUIView):
    def setup(self):
        self.form = State()
        self.form.inverse = False

    def content(self):
        with VBox():
            Checkbox('Reverse horizontal order', self.form('inverse'))
            with HBox(inverse=self.form.inverse):
                Label("Column 1")
                Spacer()
                Label("Column 2")
            with HBox(inverse=self.form.inverse):
                Label("Column 1")
                Label("Column 2").layout(weight=1)
                Label("Column 3")
        Spacer()
