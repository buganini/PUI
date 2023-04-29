# Imperative -> Declarative

## Old Method (removed in 9fdfd1acd1586b4d9796ffe2fb8fbdc161851da5)
```python
def find_pui():
    import inspect
    from .view import PUIView
    frame = inspect.currentframe()
    frames = []
    while frame:
        frames.insert(0, frame)
        views = [v for k,v in frame.f_locals.items() if isinstance(v, PUIView) and v.frames] # find active PUIView
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
```

## Concept
    * Build view hierarchy in thread-local-storage with enter/exit functions
    * Build node hierarchy in view.frames with enter/exit functions
## View Root Searching
```python
tls = threading.local()

def find_puiview():
    try:
        return tls.puistack[-1]
    except:
        raise PuiViewNotFoundError()
```

### View Root
```python
class PUIView(PUINode):
    def __init__(self):
        self.frames = []
        self.last_children = []
        super().__init__()

    def __enter__(self):
        if not hasattr(tls, "puistack"):
            tls.puistack = []
        tls.puistack.append(self)
        self.root.frames.append(self)
        return self

    def __exit__(self, ex_type, value, traceback):
        tls.puistack.pop()
        self.root.frames.pop()
        if ex_type is None: # don't consume exception
            return self

    def update(self):
        self.children = []
        try:
            with self as scope: # <- target for find_pui()
                self.content() # V-DOM builder
        except:
            # prevent crash in hot-reloading
            self.children = self.last_children
            import traceback
            traceback.print_exc()

        # DOM Sync
        sync(self, self.last_children, self.children)

        self.last_children = self.children
```

### V-DOM Node
```python
class PUINode():
    def __init__(self):
        if isinstance(self, PUIView):
            self.root = self
            self.parent = self
        else:
            self.root, self.parent = find_pui()

    def __enter__(self):
        self.root.frames.append(self)
        return self

    def __exit__(self, ex_type, value, traceback):
        self.root.frames.pop()
```

### Walk-through
#### Consider this source
```python
def content():
    with HBox():
        Node1()
        with VBox():
            Node2()
        Node3()
```
#### V-DOM construction
```graphviz
digraph G {
    compound=true;
    rankdir="LR"
    node [fontsize=10, shape=box];
    subgraph cluster_0 {
        label = "Source";
        "content()"
        ->"with HBox():"
        -> "Node1()"
        -> "with VBox():"
        -> "Node2()"
        -> "exit VBox"
        -> "Node3()"
        -> "exit HBox"
        ;
    }
    subgraph cluster_1 {
        label="View Root";
        subgraph cluster_2 {
            label = "HBox";
            hs [label="", shape=none];
            Node1;
            subgraph cluster_3 {
                label = "VBox";
                vs [label="", shape=none];
                Node2;
                ve [label="", shape=none];
            }
            Node3;
            he [label="", shape=none];
            hs->Node1->vs->Node2->ve->Node3->he [style=invis];
        }
    }
    "content()"->hs[lhead=cluster_1, constraint = true];
    "with HBox():"->hs[constraint = false];
    "Node1()"->Node1[constraint = false];
    "with VBox():"->vs[constraint = false];
    "Node2()"->Node2[constraint = false];
    "exit VBox"->ve[lhead=cluster_3, constraint = false];
    "Node3()"->Node3[constraint = false];
    "exit HBox"->he[lhead=cluster_2, constraint = false];
}
```

## State
To capture the usage of state in the view, we register listener in state getter and trigger update in state setter
## Take `StateList` as an example
```python
class StateList(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        if values is None:
            self.__values = []
        else:
            self.__values = values

    def __getitem__(self, key):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values[key]

    def __setitem__(self, key, value):
        self.__values[key] = value
        for l in self.__listeners:
            l.update()
```
