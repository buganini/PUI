from .node import *
from .dom import *
from .state import StateMutationInViewBuilderError
import time

# dprint = print
dprint = lambda *x: x

class PUIView(PUINode):
    __ALLVIEWS__  = []

    @staticmethod
    def reload():
        for v in PUIView.__ALLVIEWS__:
            v.redraw()

    def __init__(self, *args):
        self.frames = []
        self.dirty = False
        self.updating = False
        super().__init__(*args)
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
        try:
            PUIView.__ALLVIEWS__.remove(self)
        except:
            pass
        return super().destroy(direct)

    def redraw(self):
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        self.sync()

    # Subview update entry point
    def sync(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = False

        dprint(f"Sync subview {self.key}@{id(self)} retired_by={id(self.retired_by) if self.retired_by else None}")

        last_children = self.children
        try:
            self.update()
        except StateMutationInViewBuilderError:
            raise
        except:
            # prevent crash in hot-reloading
            self.children = last_children
            import traceback
            print("## <ERROR OF content() >", self.key, id(self))
            traceback.print_exc()
            print("## </ERROR OF content()>")

        if self.pui_vparent:
            self.pui_vparent.sync()
        else:
            start = time.time()
            dprint("sync() start", self.key)
            sync(self, self, 0, last_children, self.children)
            dprint(f"sync() time: {time.time()-start:.5f}", self.key)

        self.updating = False
        if self.dirty:
            self.redraw()

    def update(self, prev=None, vparent=None):
        if self.retired_by:
            return
        if self.destroyed:
            return
        if not prev:
            if self.setup:
                self.setup()
                self.setup = None
        else:
            self.setup = None
        update_start = time.time()
        dprint("update()", self.key)
        if prev and prev is not self:
            self.children = prev.children
            prev.retired_by = self
            try:
                PUIView.__ALLVIEWS__.remove(prev)
            except:
                pass

        self.children = []
        dprint(f"content() start", self.key)
        start = time.time()
        with self as scope: # init frame stack
            self.content() # V-DOM builder
        dprint(f"content() time: {time.time()-start:.5f}", self.key)

        # print("PUIView.update", self) # print DOM
        dprint(f"update() time: {time.time()-update_start:.5f}", self.key)

    def setup(self):
        pass

    def run(self):
        self.sync()
        self.start()
