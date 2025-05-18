from .config import *

@PUI
def StackExample():
    with VBox():
        with Stack():
            Label("Bottom").style(fontSize=48)
            Label("Top").style(fontSize=32, color=0xFF0000)
        Spacer()