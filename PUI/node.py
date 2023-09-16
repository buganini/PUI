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
    outoforder = False
    def __init__(self, *args):
        from .view import PUIView

        if not hasattr(self, "name"):
            self.name = None

        self.destroyed = False
        self.retired_by = None
        self._debug = 0
        self._tag = ""

        self.layout_weight = None
        self.layout_width = None
        self.layout_height = None
        self.layout_padding = None
        self.layout_margin = None
        self.style_color = None
        self.style_bgcolor = None
        self.style_fontsize = None
        self.style_fontweight = None
        self.style_fontfamily = None

        self.onClicked = None

        self.ui = None
        self.args = args
        try:
            self.root = find_puiview()
            self.parent = self.root.frames[-1]
        except PuiViewNotFoundError:
            self.root = self
            self.parent = self
            self.frames = []

        if isinstance(self, PUIView):
            self.root = self

        self.genKey()

        self.children = []

        if self.parent is self:
            self._path = tuple()
        else:
            self._path = self.parent._path + tuple([len(self.parent.children)])
            self.parent.children.append(self)

        # print(type(self).__name__, self._path, "parent=", self.parent._path)

    def genKey(self):
        # key has to be relative to PUIView, so that it can be identical when a sub-PUIView is updated individually
        self.key = "|".join([x.name or type(x).__name__ for x in self.root.frames]+[self.name or type(self).__name__]+[str(id(x)) for x in self.args])
        if self._tag:
            self.key += f"@{self._tag}"

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

    def postUpdate(self):
        pass

    def preSync(self):
        pass

    def postSync(self):
        pass

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

    def tag(self, name):
        self._tag = name
        self.genKey()
        return self

    def get_node(self):
        node = self
        while node.retired_by:
            node = node.retired_by
        return node

    def __repr__(self):
        segs = []
        headline = [
            "  "*len(self._path),
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
            segs.append("  "*(len(self._path)+1))
            segs.append("# ")
            segs.append(comment)
            segs.append("\n")

        for i,c in enumerate(self.children):
            if i > 0:
                segs.append(",\n")
            segs.append(c.__repr__())
        segs.append("\n")
        segs.append("".join(["  "*len(self._path), "}"]))
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

    def style(self, color=None, bgColor=None, fontSize=None, fontWeight=None, fontFamily=None):
        if not color is None:
            self.style_color = color
        if not bgColor is None:
            self.style_bgcolor = bgColor
        if not fontSize is None:
            self.style_fontsize = fontSize
        if not fontWeight is None:
            self.style_fontweight = fontWeight
        if not fontFamily is None:
            self.style_fontfamily = fontFamily

        return self

    def click(self, callback, *cb_args, **cb_kwargs):
        self.onClicked = callback
        self.click_args = cb_args
        self.click_kwargs = cb_kwargs
        return self

    def _clicked(self, *args, **kwargs):
        node = self.get_node()
        if node.onClicked:
            node.onClicked(*node.click_args, **node.click_kwargs)

    def flet(self, **kwargs):
        return self

    def textual(self, **kwargs):
        return self

    def tkinter(self, **kwargs):
        return self

    def qt(self, **kwargs):
        return self
