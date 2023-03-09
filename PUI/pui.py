import inspect

class PUI:
    def __init__(self, name="PUI", path=None, key=None):
        self.name = name
        self.key = key
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
        segs.append("".join(["  "*len(self.path), self.name, " { # ", self.key or "Root", "\n"]))
        for i,c in enumerate(self.children):
            if i > 0:
                segs.append(",\n")
            segs.append(c.__repr__())
        segs.append("\n")
        segs.append("".join(["  "*len(self.path), "}"]))
        return "".join(segs)

def Container(func):
    def wrapper(*args, **kwargs):
        parents = inspect.getouterframes(inspect.currentframe())
        outer = parents[1]
        key = f"{outer.filename}:{outer.lineno}"
        for p in parents:
            puis = [v for k,v in p.frame.f_locals.items() if isinstance(v, PUI) and v.active]
            if puis:
                puis.sort(key=lambda x:x.path)
                return func(puis[-1], key, *args, **kwargs)
        raise RuntimeError("PUI Context Not Found")
    return wrapper

@Container
def HStack(ctx, key, name):
    if name is None:
        name = ""
    else:
        name = f"/{name}"
    n = PUI(f"HStack{name}", path=ctx.path+tuple([len(ctx.children)]), key=key)
    ctx.children.append(n)
    return n

if __name__=="__main__":
    def build_ui():
        with PUI() as pui:
            with HStack("a") as scope:
                HStack("b")
            HStack("c")
        return pui
        
    print(build_ui())