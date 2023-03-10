from .node import *

class PUIView(PUINode):
    def __init__(self):
        super().__init__()
        self.last_content = None

    def content(self):
        return None

    def update(self):
        with self as scope:
            content = self.content()

        if self.ui is None:
            self.ui = self.inflate()

        if self.last_content is None:
            for c in self.children:
                c.ui = c.inflate()
                self.addChild(c)

        self.last_content = content

    def run(self):
        self.update()
        self.start()
