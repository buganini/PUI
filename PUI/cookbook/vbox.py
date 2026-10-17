from .config import *

class VBoxExample(PUIView):
    def content(self):
        with VBox():
            Label("Row 1")
            Divider()
            Label("Row 2")
            Spacer()
