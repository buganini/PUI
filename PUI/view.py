from .node import *
from .dom import *
import time

# dprint = print
dprint = lambda *x: x

class PUIView(PUINode):
    terminal = True
    __ALLVIEWS__  = []

    @staticmethod
    def reload():
        for v in PUIView.__ALLVIEWS__:
            v.redraw()

    def __init__(self, *args, **kwargs):
        self.frames = []
        self.dirty = False
        self.updating = False
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

    def content(self):
        return None

    def dump(self):
        dprint(f"content() start", self.key)
        start = time.time()
        with self as scope:
            self.content()
        dprint(f"content() time: {time.time()-start:.5f}", self.key)
        return scope

    def destroy(self, direct):
        PUIView.__ALLVIEWS__.remove(self)
        return super().destroy(direct)

    def redraw(self):
        self.update(redraw=True)

    def update(self, prev=None, redraw=False):
        if self.retired_by:
            return
        if self.destroyed:
            return
        if not prev and not redraw:
            self.setup()
        update_start = time.time()
        dprint("update()", self.key)
        if prev:
            self.children = prev.children
            prev.retired_by = self
            PUIView.__ALLVIEWS__.remove(prev)

        last_children = self.children
        self.children = []
        try:
            dprint(f"content() start", self.key)
            start = time.time()
            with self as scope: # init frame stack
                self.content() # V-DOM builder
            dprint(f"content() time: {time.time()-start:.5f}", self.key)
        except:
            # prevent crash in hot-reloading
            self.children = last_children
            import traceback
            print("## <ERROR OF content() >", self.key, id(self))
            traceback.print_exc()
            print("## </ERROR OF content()>")
            return

        # print("PUIView.update", self) # print DOM

        start = time.time()
        dprint("sync() start", self.key)
        sync(self, last_children, self.children)
        dprint(f"sync() time: {time.time()-start:.5f}", self.key)

        dprint(f"update() time: {time.time()-update_start:.5f}", self.key)

    def setup(self):
        pass

    def run(self):
        self.redraw()
        self.start()
