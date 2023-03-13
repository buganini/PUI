from .node import *
from .dom import *
class PUIView(PUINode):
    def __init__(self):
        self.ready = True
        self.frames = []
        self.last_children = []
        super().__init__()

    def content(self):
        return None

    def dump(self):
        with self as scope:
            self.content()
        return scope

    def update(self):
        if not self.ready:
            return
        self.children = []
        with self as scope: # CRITICAL: this is the searching target for find_pui()
            self.content()

        # print(self) # print DOM
        sync(self, self.last_children, self.children)

        self.last_children = self.children

    def run(self):
        self.update()
        self.start()
