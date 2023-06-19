from .config import *

class QtMdiExample(PUIView):
    def content(self):
        with MdiArea():
            with MdiSubWindow():
                with VBox():
                    Label("1")
                    Label("2")
            with MdiSubWindow():
                with VBox():
                    Label("A")
                    Label("B")
