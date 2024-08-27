from .config import *

class TabExample(PUIView):
    def content(self):
        with Tabs():
            with Tab("Tab 1"):
                Label("Content 1")
            with Tab("Tab 2"):
                Label("Content 2")


if __name__ == '__main__':
    @PUIApp
    def App():
        with Window():
           TabExample()
    App().run()