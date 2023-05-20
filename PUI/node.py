import threading
from .utils import *

tls = threading.local()

class PuiViewNotFoundError(Exception): pass

def find_puiview():
    try:
        return tls.puistack[-1]
    except:
        raise PuiViewNotFoundError()

class PUINode():
    supported = True
    terminal = False
    def __init__(self, *args):
        from .view import PUIView

        if not hasattr(self, "name"):
            self.name = None

        self.destroyed = False
        self.retired_by = None
        self._debug = 0

        self.layout_weight = None
        self.layout_width = None
        self.layout_height = None
        self.layout_padding = None
        self.layout_margin = None

        self.onClicked = None

        self.ui = None
        self.args = args
        try:
            self.root = find_puiview()
            self.parent = self.root.frames[-1]
        except PuiViewNotFoundError:
            self.root = self
            self.parent = self

        if isinstance(self, PUIView):
            self.root = self

        # key has to be relative to PUIView, so that it can be identical when a sub-PUIView is updated individually
        self.key = "|".join([x.name or type(x).__name__ for x in self.root.frames]+[self.name or type(self).__name__]+[str(id(x)) for x in self.args])

        self.children = []

        if self.parent is self:
            self.path = tuple()
        else:
            self.path = self.parent.path + tuple([len(self.parent.children)])
            self.parent.children.append(self)
        # print(type(self).__name__, self.path, "parent=", self.parent.path)

    def __enter__(self):
        # print("enter", type(self).__name__, id(self))
        self.root.frames.append(self)
        return self

    def __exit__(self, ex_type, value, traceback):
        # print("exit", type(self).__name__, id(self))
        self.root.frames.pop()
        if ex_type is None: # don't consume exception
            return self

    @property
    def inner(self):
        if self.ui:
            return self.ui
        return self.parent.inner

    @property
    def outer(self):
        if self.ui:
            return self.ui
        if self.children:
            return self.children[0].outer
        return None

    def comment(self):
        return None

    def update(self, prev):
        if prev:
            prev.retired_by = self

    def destroy(self, direct):
        self.root = None
        self.parent = None

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def debug(self, level=1):
        self._debug = level
        return self

    def get_node(self):
        node = self
        while node.retired_by:
            node = node.retired_by
        return node

    def __repr__(self):
        segs = []
        headline = [
            "  "*len(self.path),
            self.name or type(self).__name__,
            # f"@{str(id(self))}", # print view id
            " {",
        ]

        # print view key
        headline.append(" # ")
        headline.append(self.key)

        headline.append("\n")
        segs.append("".join(headline))

        comment = self.comment()
        if comment:
            segs.append("  "*(len(self.path)+1))
            segs.append("# ")
            segs.append(comment)
            segs.append("\n")

        for i,c in enumerate(self.children):
            if i > 0:
                segs.append(",\n")
            segs.append(c.__repr__())
        segs.append("\n")
        segs.append("".join(["  "*len(self.path), "}"]))
        return "".join(segs)

    def layout(self, width=None, height=None, weight=None, padding=None, margin=None):
        if not width is None:
            self.layout_width = width
        if not height is None:
            self.layout_height = height
        if not weight is None:
            self.layout_weight = weight
        if not padding is None:
            self.layout_padding = trbl(padding)
        if not margin is None:
            self.layout_margin = trbl(margin)

        return self

    def click(self, callback, *cb_args, **cb_kwargs):
        self.onClicked = callback
        self.click_args = cb_args
        self.click_kwargs = cb_kwargs
        return self

    def _clicked(self, *args, **kwargs):
        node = self.get_node()
        if node.onClicked:
            node.onClicked(*self.click_args, **self.click_kwargs)

    def flet(self, **kwargs):
        return self

    def textual(self, **kwargs):
        return self

    def tk(self, **kwargs):
        return self

    def qt(self, **kwargs):
        return self
