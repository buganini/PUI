from .config import *

@PUI
def LabelExample():
    with VBox():
        Label("Hello World")
        Label(text="No <b>HTML</b>")
        Spacer()