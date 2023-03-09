import inspect

class PUI:
    def __init__(self, name="PUI", path=None):
        self.name = name
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
        return self
    
    def __repr__(self):
        segs = []
        segs.append("".join(["  "*len(self.path), self.name, " {\n"]))
        for i,c in enumerate(self.children):
            if i > 0:
                segs.append(",\n")
            segs.append(c.__repr__())
        segs.append("\n")
        segs.append("".join(["  "*len(self.path), "}"]))
        return "".join(segs)

def __find_context():
    parents = inspect.getouterframes(inspect.currentframe())
    for p in parents:
        puis = [v for k,v in p.frame.f_locals.items() if isinstance(v, PUI) and v.active]
        if puis:
            puis.sort(key=lambda x:x.path)
            return puis[-1]
    return None

def HStack(name=None):
    ctx = __find_context()
    if ctx is None:
        raise RuntimeError("PUI Context Not Found")

    if name is None:
        name = ""
    else:
        name = f"/{name}"
    n = PUI(f"HStack{name}", path=ctx.path+tuple([len(ctx.children)]))
    ctx.children.append(n)
    return n

if __name__=="__main__":
    def setContent():
        with PUI() as pui:
            with HStack("a") as scope:
                HStack("b")
            HStack("c")
            return pui
        
    print(setContent())