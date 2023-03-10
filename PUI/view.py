from .node import *

class PUIView(PUINode):
    def __init__(self):
        super().__init__()
        self.last_children = []

    def content(self):
        return None

    def update(self):
        self.children = []
        with self as scope:
            self.content()

        print("update")

        if self.ui is None:
            self.ui = self.inflate()

        if self.last_children is None:
            for c in self.children:
                print("inflate")
                c.ui = c.inflate()
                self.addChild(c)

        self.last_children = self.children

    def run(self):
        self.update()
        self.start()
