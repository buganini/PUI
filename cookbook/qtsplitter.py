from .config import *

class QtSplitterExample(PUIView):
    def content(self):
        with QtSplitter(vertical=True):
            with QtSplitter():
                with VBox():
                    Label("item 1")
                    Label("item 2")
                    Label("item 3")
                    Label("item 4")

                Label("pane").qt(StyleSheet={"background-color":"gray"})

            Text("blah blah").qt(StyleSheet={"background-color":"gray"})
