from PUI.PySide6 import *

@PUI
def ScrollExample():
    with Scroll():
        with VBox():
            for i in range(50):
                Label(f"Row {i+1}")
