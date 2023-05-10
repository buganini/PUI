from PUI.PySide6 import *

@PUI
def VBoxExample():
    with VBox():
        Label("Row 1")
        Label("Row 2")
        Spacer()