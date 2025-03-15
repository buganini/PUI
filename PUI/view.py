from .node import *
from .dom import *
from .state import StateMutationInViewBuilderError
import time

DEBUG = False

class PUIView(PUINode):
    pui_virtual = True
    pui_isview = True
    __ALLVIEWS__  = []

    @staticmethod
    def reload():
        for v in PUIView.__ALLVIEWS__:
            if DEBUG:
                print("reload", v.key)
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
        if DEBUG:
            print(f"content() start", self.key)
        start = time.time()
        with self as scope:
            self.content()
        if DEBUG:
            print(f"content() time: {time.time()-start:.5f}", self.key)
        return scope

    def destroy(self, direct):
        try:
            PUIView.__ALLVIEWS__.remove(self)
        except:
            pass
        return super().destroy(direct)

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        self.sync()

    def wait(self):
        """
        Wait for the view to be updated.
        """
        while self.updating or self.dirty:
            time.sleep(0.0001)

    # Subview update entry point
    def sync(self):
        if not self.pui_virtual:
            raise VDomError(f"sync() called on non-virtual node {self.key}")
        if self.retired_by or self.destroyed:
            return
        self.dirty = False

        dom_parent = (self.pui_dom_parent or self).get_node()
        if DEBUG:
            print(f"Sync subview {self.key}@{id(self)} retired_by={id(self.retired_by) if self.retired_by else None} destroyed={self.destroyed} dom_parent={dom_parent.key}@{id(dom_parent)}")
        found, offset = dom_parent.findDomOffsetForNode(self)
        if DEBUG:
            print(f"    found={found} offset={offset}")
        if not found:
            if DEBUG:
                print(dom_parent.serialize(show_pyid=True, show_hierarchy=True))
            offset = 0

        last_children = self.children
        try:
            self.update()
        except (StateMutationInViewBuilderError, VDomError):
            raise
        except:
            # prevent crash in hot-reloading
            self.children = last_children
            import traceback
            print("## <ERROR OF content() >", self.key, id(self))
            traceback.print_exc()
            print("## </ERROR OF content()>")

        start = time.time()
        if DEBUG:
            print("sync() start", self.key)

        if DEBUG:
            print(f"offset for {self.key}@{id(self)} on {dom_parent.key}@{id(dom_parent)} is {offset}")
        sync(self, dom_parent, offset, last_children, self.children)
        if DEBUG:
            print(f"sync() time: {time.time()-start:.5f}", self.key)

        self.updating = False
        if self.dirty:
            self.redraw()

    def update(self, prev=None):
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

        if DEBUG:
            print(f"update() {self.key}@{id(self)} prev={id(prev) if prev else None}")

        if prev and prev is not self:
            prev.retired_by = self
            try:
                print(f"retired {prev.key}@{id(prev)}")
                PUIView.__ALLVIEWS__.remove(prev)
            except:
                pass

        self.children = []
        if DEBUG:
            print(f"content() start", self.key)
        start = time.time()
        with self as scope: # init frame stack
            self.content() # V-DOM builder
        if DEBUG:
            print(f"content() time: {time.time()-start:.5f}", self.key)

    def setup(self):
        pass

    def run(self):
        self.sync()
        self.start()
