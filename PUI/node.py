import threading

tls = threading.local()

class PuiViewNotFoundError(Exception): pass

def find_puiview():
    try:
        return tls.puistack[-1]
    except:
        raise PuiViewNotFoundError()

class PUINode():
    terminal = False
    def __init__(self, *args):
        from .view import PUIView

        if not hasattr(self, "name"):
            self.name = None

        self._debug = 0

        self.layout_weight = None
        self.layout_width = None
        self.layout_height = None

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
        return self.ui

    @property
    def outer(self):
        return self.ui

    def comment(self):
        return None

    def update(self, prev):
        return None

    def destroy(self):
        self.root = None
        self.parent = None

    def addChild(self, idx, ui):
        pass

    def removeChild(self, idx, ui):
        pass

    def debug(self, level=1):
        self._debug = level
        return self

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

    def layout(self, width=None, height=None, weight=None):
        if not width is None:
            self.layout_width = width
        if not height is None:
            self.layout_height = height
        if not weight is None:
            self.layout_weight = weight

        return self

    def click(self, callback):
        print(f"click() not implemented for {self.__class__.__name__}")
        return self

    def qt(self, **kwargs):
        return self
