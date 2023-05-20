from .config import *

class QtMdiExample(PUIView):
    def content(self):
        with QtMdiArea():
            with QtMdiSubWindow():
                with VBox():
                    Label("1")
                    Label("2")
            with QtMdiSubWindow():
                with VBox():
                    Label("A")
                    Label("B")
