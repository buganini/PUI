from .config import *

@PUI
def LabelExample():
    with VBox():
        Label("Hello World")
        Label("Big Yellow").style(fontSize=20, color=0xFFFF00, bgColor=0xFF0000)
        Label(text="No <b>HTML</b>")
        Spacer()