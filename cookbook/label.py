from .config import *

@PUI
def LabelExample():
    with VBox():
        Label("Hello World")
        Label("No <b>HTML</b>")
        Spacer()