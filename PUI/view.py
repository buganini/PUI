from .node import *
from .dom import *
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

        sync(self, self.last_children, self.children)

        self.last_children = self.children

    def run(self):
        self.update()
        self.start()
