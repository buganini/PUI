from .config import *

@PUI
def HBoxExample():
    with HBox():
        Label("Column 1")
        Spacer()
        Label("Column 2")
