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
            Spacer()
