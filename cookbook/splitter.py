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

                Label("pane").qt(StyleSheet={"background-color":"gray"})

            Text("blah blah").qt(StyleSheet={"background-color":"gray"})
