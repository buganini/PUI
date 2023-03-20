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
        raise RuntimeError("PUIView not found")

class PUINode():
    def __init__(self):
        from .view import PUIView
        self.layout_weight = None
        self.ui = None
        if isinstance(self, PUIView):
            self.root = self
            self.parent = self
            self.key = "|".join([type(x).__name__ for x in self.root.frames]+[type(self).__name__])
        else:
            self.root, self.parent, key = find_pui()
            self.key = "|".join([type(x).__name__ for x in self.root.frames]+[type(self).__name__]+[key])

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
            type(self).__name__,
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

    def layout(self, weight=None):
        if not weight is None:
            self.layout_weight = weight
        return self

    def weight(self, v):
        self.layout_weight = v
        return self