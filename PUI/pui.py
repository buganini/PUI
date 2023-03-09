import inspect

class PUI:
    def __init__(self, name="PUI", path=None, key=None, comment=""):
        self.name = name
        self.key = key
        self.comment = comment
        if path is None:
            self.path = tuple()
        else:
            self.path = path
        self.children = []
        self.active = False

    def __enter__(self):
        self.active = True
        return self

    def __exit__(self, type, value, traceback):
        self.active = False
        if type is None:
            return self

    def __repr__(self):
        segs = []
        headline = [
            "  "*len(self.path),
            self.name,
            " { # ",
        ]

        if self.comment:
            headline.append(self.comment)
            headline.append(", ")

        headline.append(self.key or "Root")
        headline.append("\n")
        segs.append("".join(headline))
        for i,c in enumerate(self.children):
            if i > 0:
                segs.append(",\n")
            segs.append(c.__repr__())
        segs.append("\n")
        segs.append("".join(["  "*len(self.path), "}"]))
        return "".join(segs)

def PUIElement(func):
    def wrapper(*args, **kwargs):
        parents = inspect.getouterframes(inspect.currentframe())
        outer = parents[1]
        key = f"{outer.filename}:{outer.lineno}"
        for p in parents:
            puis = [v for k,v in p.frame.f_locals.items() if isinstance(v, PUI) and v.active]
            if puis:
                puis.sort(key=lambda x:x.path)
                ctx = puis[-1]
                n = func(ctx, key, *args, **kwargs)
                ctx.children.append(n)
                return n

        raise RuntimeError("PUI Context Not Found")
    return wrapper
