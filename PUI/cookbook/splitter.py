from .config import *

class SplitterExample(PUIView):
    def content(self):
        with Splitter(vertical=True):
            with Splitter():
                with VBox():
                    Label("item 1")
                    Label("item 2")
                    Label("item 3")
                    Label("item 4")

                Label("pane 2").style(bgColor=0x244B5A, color=0xFFF7E6).tStyle(
                    bgColor=0x244B5A, color=0xFFF7E6,
                )
                Label("pane 3").style(bgColor=0xD3B98B, color=0x1C2A30).tStyle(
                    bgColor=0xD3B98B, color=0x1C2A30,
                )

            Text("blah blah").style(bgColor=0xF2E6CF, color=0x1C2A30).tStyle(
                bgColor=0xF2E6CF, color=0x1C2A30,
            )
