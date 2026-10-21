from .config import *

class StackExample(PUIView):
    def content(self):
        with VBox():
            with Stack():
                Label("Bottom").style(fontSize=48, color=0x244B5A).tStyle(
                    color=0xFFF7E6,
                )
                Label("Top").style(fontSize=32, color=0xA84A3A).tStyle(
                    color=0xD3B98B,
                )
            Spacer()
