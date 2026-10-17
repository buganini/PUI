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

                Label("pane 2").style(bgColor=0xCCCCCC)
                Label("pane 3").style(bgColor=0xDDDDDD)

            Text("blah blah").style(bgColor=0xCCCCCC)
