import inspect

class PUINode():
    def __init__(self):
        self.active = False
        self.ui = None

        parents = inspect.getouterframes(inspect.currentframe())
        for p in parents:
            puis = [v for k,v in p.frame.f_locals.items() if isinstance(v, PUINode) and v.active]
            if puis:
                puis.sort(key=lambda x:x.path)
                self.parent = puis[-1]
                break
        else:
            self.parent = self

        self.children = []

        if self.parent is self:
            self.path = tuple()
        else:
            self.path = self.parent.path + tuple([len(self.parent.children)])
            self.parent.children.append(self)

    def __enter__(self):
        self.active = True
        return self

    def __exit__(self, type, value, traceback):
        self.active = False
        if type is None:
            return self

    def comment(self):
        return None

    def inflate(self):
        return None
    
    def addUI(self, ui):
        pass

    def __repr__(self):
        segs = []
        headline = [
            "  "*len(self.path),
            type(self).__name__,
            " {",
            "\n"
        ]
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
