from .config import *

@PUI
def HBoxExample():
    with VBox():
        with HBox():
            Label("Column 1")
            Spacer()
            Label("Column 2")
        with HBox():
            Label("Column 1")
            Label("Column 2").layout(weight=1)
            Label("Column 3")
