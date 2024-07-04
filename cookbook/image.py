from .config import *

class ImageExample(PUIView):
    def content(self):
        with VBox():
            Image("screenshots/hello_world.png").layout(height=360)
            Spacer()
