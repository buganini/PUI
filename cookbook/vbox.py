from .config import *

@PUI
def VBoxExample():
    with VBox():
        Label("Row 1")
        Divider()
        Label("Row 2")
        Spacer()