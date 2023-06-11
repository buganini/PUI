from .config import *

class TabExample(PUIView):
    def content(self):
        with Tabs():
            with Tab("Tab 1"):
                Label("Content 1")
            with Tab("Tab 2"):
                Label("Content 2")
