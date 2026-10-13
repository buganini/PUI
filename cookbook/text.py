from .config import *

class TextExample(PUIView):
    def content(self):
        with VBox():
            Text("Multiple\nLines\nText")
            Html('<i>HTML</i> <a style="color:red">support</a>')
            MarkDown("# H1\n## H2\n* item 1\n* item 2")
            Spacer()
