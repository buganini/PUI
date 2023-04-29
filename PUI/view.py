from .node import *
from .dom import *
import time

# dprint = print
dprint = lambda *x: x

class PUIView(PUINode):
    __ALLVIEWS__  = []

    @staticmethod
    def reload():
        for v in PUIView.__ALLVIEWS__:
            v.redraw()

    def __init__(self, *args, **kwargs):
        self.children_first = True # default to bottom-up
        self.frames = []
        self.last_children = []
        super().__init__(*args, **kwargs)
        PUIView.__ALLVIEWS__.append(self)

    def __enter__(self):
        if not hasattr(tls, "puistack"):
            tls.puistack = []
        tls.puistack.append(self)
        # print("enter", type(self).__name__, id(self))
        self.root.frames.append(self)
        return self

    def __exit__(self, ex_type, value, traceback):
        tls.puistack.pop()
        # print("exit", type(self).__name__, id(self))
        self.root.frames.pop()
        if ex_type is None: # don't consume exception
            return self

    def destroy(self):
        PUIView.__ALLVIEWS__.remove(self)
        return super().destroy()

    def content(self):
        return None

    def dump(self):
        dprint(f"content() start", self.key)
        start = time.time()
        with self as scope:
            self.content()
        dprint(f"content() time: {time.time()-start:.5f}", self.key)
        return scope

    def redraw(self):
        self.update()

    def update(self, prev=None):
        update_start = time.time()
        dprint("update()", self.key)
        if prev:
            self.last_children = prev.children

        self.children = []
        try:
            dprint(f"content() start", self.key)
            start = time.time()
            with self as scope: # CRITICAL: this is the searching target for find_pui()
                self.content() # V-DOM builder
            dprint(f"content() time: {time.time()-start:.5f}", self.key)
        except:
            # prevent crash in hot-reloading
            self.children = self.last_children
            import traceback
            print("## <ERROR OF content() >")
            traceback.print_exc()
            print("## </ERROR OF content()>")


        # print("PUIView.update", self) # print DOM

        start = time.time()
        dprint("sync() start", self.key)
        sync(self, self.last_children, self.children, self.children_first)
        dprint(f"sync() time: {time.time()-start:.5f}", self.key)

        self.last_children = self.children
        dprint(f"update() time: {time.time()-update_start:.5f}", self.key)

    def run(self):
        self.redraw()
        self.start()
