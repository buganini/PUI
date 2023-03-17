from .node import *
from .dom import *

class PUIView(PUINode):
    __ALLVIEWS__  = []

    @staticmethod
    def reload():
        for v in PUIView.__ALLVIEWS__:
            v.redraw()

    def __init__(self):
        self.children_first = True # default to bottom-up
        self.frames = []
        self.last_children = []
        super().__init__()
        PUIView.__ALLVIEWS__.append(self)

    def destroy(self):
        PUIView.__ALLVIEWS__.remove(self)
        return super().destroy()

    def content(self):
        return None

    def dump(self):
        with self as scope:
            self.content()
        return scope

    def redraw(self):
        self.update()

    def update(self):

        self.children = []
        try:
            with self as scope: # CRITICAL: this is the searching target for find_pui()
                self.content() # V-DOM builder
        except:
            # prevent crash in hot-reloading
            self.children = self.last_children
            import traceback
            traceback.print_exc()


        # print(self) # print DOM
        sync(self, self.last_children, self.children, self.children_first)

        self.last_children = self.children

    def run(self):
        self.update()
        self.start()
