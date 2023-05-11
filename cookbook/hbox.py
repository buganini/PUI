from .config import *

@PUI
def HBoxExample():
    with HBox():
        Label("Column 1")
        Label("Column 2")
        Spacer()