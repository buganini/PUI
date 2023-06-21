from .config import *

@PUI
def ScrollExample():
    with Scroll().scrollY(-1):
        with VBox():
            for i in range(50):
                Label(f"Row {i+1}")
