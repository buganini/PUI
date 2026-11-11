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
                Divider()
                Spacer()
                Label("Column 2")
            with HBox(inverse=self.form.inverse):
                Label("Column 1")
                Divider()
                Label("Column 2").layout(weight=1)
                Divider()
                Label("Column 3")
            Divider()
            Label("Default gap: 0")
            with HBox(inverse=self.form.inverse):
                Label("First")
                Label("Second")
                Label("Third")
            Divider()
            Label("gap=12 pixels / tGap=2 cells")
            with HBox(inverse=self.form.inverse, gap=12, tGap=2):
                Label("First")
                Label("Second")
                Label("Third")
        Spacer()
