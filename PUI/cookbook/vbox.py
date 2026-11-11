from .config import *

class VBoxExample(PUIView):
    def setup(self):
        self.form = State()
        self.form.inverse = False

    def content(self):
        with VBox():
            Checkbox('Reverse vertical order', self.form('inverse'))
            with VBox(inverse=self.form.inverse).layout(weight=1):
                Label("Row 1")
                Divider()
                Label("Row 2")
            Divider()
            Label("Default gap: 10 pixels / tGap: 0 cells")
            with VBox(inverse=self.form.inverse):
                Label("First")
                Label("Second")
                Label("Third")
            Divider()
            Label("gap=12 pixels / tGap=1 cell")
            with VBox(inverse=self.form.inverse, gap=12, tGap=1):
                Label("First")
                Label("Second")
                Label("Third")
            Spacer()
