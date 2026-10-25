from .config import *

class TextExample(PUIView):
    def content(self):
        with VBox():
            Text("Multiple\nLines\nText")
            Html('<i>HTML</i> <span style="color:#244b5a">support</span>').style(
                color=0x1C2A30, bgColor=0xFFF7E6,
            )
            if MarkDown.pui_supported:
                MarkDown("# H1\n## H2\n* item 1\n* item 2")
            else:
                Label('Markdown is not implemented by this backend')
            Spacer()
