import threading

tls = threading.local()

class PuiViewNotFoundError(Exception): pass

def find_puiview():
    try:
        return tls.puistack[-1]
    except:
        raise PuiViewNotFoundError()

def find_pui():
    import inspect
    from .view import PUIView
    frame = inspect.currentframe()
    frames = []
    while frame:
        frames.insert(0, frame)
        views = [v for k,v in frame.f_locals.items() if isinstance(v, PUIView) and v.frames]
        if views:
            root = views[0]
            parent = root.frames[-1]

            for f in frames:
                fi = inspect.getframeinfo(f)
                # print(repr(fi.function), fi.filename, fi.lineno)
                if fi.function != "__wrapped_content__":
                    key = f"{fi.filename}:{fi.lineno}"
                    break

            return root, parent, key
        frame = frame.f_back
    else:
        raise PuiViewNotFoundError()

class PUINode():
    terminal = False
    def __init__(self, *args):
        from .view import PUIView

        if not hasattr(self, "name"):
            self.name = None

        self.layout_weight = None
        self.layout_width = None
        self.layout_height = None

        self.ui = None
        self.args = args
        try:
            self.root, self.parent, key = find_pui()
            key = [key]
        except PuiViewNotFoundError:
            self.root = self
            self.parent = self
            key = []

        if isinstance(self, PUIView):
            self.root = self

        # key has to be related to PUIView, so that it can be identical when a sub-PUIView is locally updated
        self.key = "|".join([x.name or type(x).__name__ for x in self.root.frames]+[self.name or type(self).__name__]+key+[str(id(x)) for x in self.args])

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

    def comment(self):
        return None

    def update(self, prev):
        return None

    def destroy(self):
        return None

    def addChild(self, idx, ui):
        pass

    def removeChild(self, idx, ui):
        pass

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
