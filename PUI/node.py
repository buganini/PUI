import threading
from .utils import *
from .dom import *

tls = threading.local()

class PuiViewNotFoundError(Exception): pass

def find_puiview():
    try:
        return tls.puistack[-1]
    except:
        raise PuiViewNotFoundError()

class PUIEvent():
    def __str__(self):
        return str(self.__dict__)


class PUINode():
    # To prevent crashes when we use a UI component not supported by the selected backend, this is useful when you are trying to support multiple backends.
    pui_supported = True

    # Tell DOM syncer not to go deeper into the node, it should be True for non-container elements
    pui_terminal = False

    # Menu and window-like UI elements, are out-of-order, so they are moved to the end of siblings before DOM syncing to simplify the process
    pui_outoforder = False

    # Used by PUIView
    pui_isview = False

    # Used by TimelineView, TabView, Sub-View or other nodes don't link to a real UI hierarchy
    # Children of virtual nodes will be promoted to the same level as the virtual node, addChild/removeChild won't be called for virtual nodes
    pui_virtual = False

    # Used by grid layout, when enabled, sort children by grid_{row,column,rowspan,columnspan} before DOM sync
    pui_grid_layout = False

    def __init__(self, *args):
        from .view import PUIView

        if not hasattr(self, "name"):
            self.name = None

        self.destroyed = False
        self.retired_by = None
        self.pui_dom_parent = None
        self._debug = 0
        self._id = ""

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
        self.grid_row = None
        self.grid_column = None
        self.grid_rowspan = None
        self.grid_columnspan = None

        self._onChanged = None
        self._onClicked = None
        self._onDblClicked = None
        self._onInput = None
        self._onKeyPress = None
        self._onMouseDown = None
        self._onMouseUp = None
        self._onMouseMove = None
        self._onWheel = None

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

    def findDomOffsetForNode(self, node):
        if self is node:
            return True, 0
        offset = 0
        for c in self.children:
            if c is node:
                return True, offset
            if c.pui_virtual:
                found, off = c.findDomOffsetForNode(node)
                offset += off
                if found:
                    return True, offset
            elif not c.pui_outoforder:
                offset += 1
        return False, offset

    def genKey(self):
        # key has to be relative to PUIView, so that it can be identical when a sub-PUIView is updated individually
        self.key = "|".join([x.name or type(x).__name__ for x in self.root.frames]+[self.name or type(self).__name__])
        if self.grid_row is not None and self.grid_column is not None:
            self.key += f":grid:{self.grid_row},{self.grid_column},{self.grid_rowspan},{self.grid_columnspan}"
        if hasattr(self, "_internal_tag"):
            self.key += f"%{self._internal_tag}"
        if self._id:
            self.key += f"#{self._id}"

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
    def non_virtual_parent(self):
        p = self.parent
        while p.pui_virtual:
            p = p.parent
        return p

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
        if prev and prev is not self:
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
        self.children = []

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def debug(self, level=1):
        self._debug = level
        return self

    def id(self, name):
        self._id = name
        self.genKey()
        return self

    def get_node(self):
        node = self
        while node.retired_by:
            node = node.retired_by
        if node is not self:
            self.retired_by = node
        return node

    def __repr__(self):
        return self.serialize()

    def serialize(self, show_key=True, show_pyid=False, show_hierarchy=False, layout_debug=False):
        segs = []
        headline = [
            "  "*len(self._path),
            self.name or type(self).__name__,
        ]
        if show_pyid:
            headline.append(f"@{id(self)}")
        if self.children:
            headline.append(" {")

        # print view key
        if show_key:
            headline.append(" # Key:  ")
            headline.append(self.key)

        if show_hierarchy:
            headline.append(f" # parent={id(self.parent) if self.parent else None}")

        if layout_debug:
            headline.append(" # Layout:")
            if hasattr(self, "expand_x"):
                headline.append(f" expand_x={self.expand_x}")
            if hasattr(self, "expand_y"):
                headline.append(f" expand_y={self.expand_y}")
            if hasattr(self, "strong_expand_x"):
                headline.append(f" strong_expand_x={self.strong_expand_x}")
            if hasattr(self, "strong_expand_y"):
                headline.append(f" strong_expand_y={self.strong_expand_y}")
            if hasattr(self, "weak_expand_x"):
                headline.append(f" weak_expand_x={self.weak_expand_x}")
            if hasattr(self, "weak_expand_y"):
                headline.append(f" weak_expand_y={self.weak_expand_y}")
            if hasattr(self, "nweak_expand_x"):
                headline.append(f" nweak_expand_x={self.nweak_expand_x}")
            if hasattr(self, "nweak_expand_y"):
                headline.append(f" nweak_expand_y={self.nweak_expand_y}")
            if hasattr(self, "strong_expand_x_children"):
                headline.append(f" strong_expand_x_children={self.strong_expand_x_children}")
            if hasattr(self, "strong_expand_y_children"):
                headline.append(f" strong_expand_y_children={self.strong_expand_y_children}")

        if self.children:
            headline.append("\n")
        segs.append("".join(headline))

        comment = self.comment()
        if comment:
            segs.append("  "*(len(self._path)+1))
            segs.append("# ")
            segs.append(comment)
            segs.append("\n")

        if self.children:
            for i,c in enumerate(self.children):
                if i > 0:
                    segs.append("\n")
                segs.append(c.serialize(show_key=show_key, show_pyid=show_pyid, show_hierarchy=show_hierarchy, layout_debug=layout_debug))
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

    def grid(self, row=None, column=None, rowspan=None, columnspan=None):
        if row is not None:
            self.grid_row = row
        if column is not None:
            self.grid_column = column
        if rowspan is not None:
            self.grid_rowspan = rowspan
        if columnspan is not None:
            self.grid_columnspan = columnspan
        self.genKey()
        return self

    def click(self, callback, *cb_args, **cb_kwargs):
        self._onClicked = callback, cb_args, cb_kwargs
        return self

    def _clicked(self, e=None, *args, **kwargs):
        node = self.get_node()
        if node._onClicked:
            cb, cb_args, cb_kwargs = node._onClicked
            cb(e, *cb_args, **cb_kwargs)

    def dblclick(self, callback, *cb_args, **cb_kwargs):
        self._onDblClicked = callback, cb_args, cb_kwargs
        return self

    def _dblclicked(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onDblClicked:
            cb, cb_args, cb_kwargs = node._onDblClicked
            cb(e, *cb_args, **cb_kwargs)

    def change(self, callback, *cb_args, **cb_kwargs):
        self._onChanged = callback, cb_args, cb_kwargs
        return self

    def _change(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onChanged:
            cb, cb_args, cb_kwargs = node._onChanged
            cb(e, *cb_args, **cb_kwargs)

    def input(self, callback, *cb_args, **cb_kwargs):
        self._onInput = callback, cb_args, cb_kwargs
        return self

    def _input(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onInput:
            cb, cb_args, cb_kwargs = node._onInput
            cb(e, *cb_args, **cb_kwargs)

    def mousedown(self, callback, *cb_args, **cb_kwargs):
        self._onMouseDown = callback, cb_args, cb_kwargs
        return self

    def _mousedown(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseDown:
            cb, cb_args, cb_kwargs = node._onMouseDown
            cb(e, *cb_args, **cb_kwargs)

    def mouseup(self, callback, *cb_args, **cb_kwargs):
        self._onMouseUp = callback, cb_args, cb_kwargs
        return self

    def _mouseup(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseUp:
            cb, cb_args, cb_kwargs = node._onMouseUp
            cb(e, *cb_args, **cb_kwargs)

    def mousemove(self, callback, *cb_args, **cb_kwargs):
        self._onMouseMove = callback, cb_args, cb_kwargs
        return self

    def _mousemove(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseMove:
            cb, cb_args, cb_kwargs = node._onMouseMove
            cb(e, *cb_args, **cb_kwargs)

    def wheel(self, callback, *cb_args, **cb_kwargs):
        self._onWheel = callback, cb_args, cb_kwargs
        return self

    def _wheel(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onWheel:
            cb, cb_args, cb_kwargs = node._onWheel
            cb(e, *cb_args, **cb_kwargs)

    def keypress(self, callback, *cb_args, **cb_kwargs):
        self._onKeyPress = callback, cb_args, cb_kwargs
        return self

    def _keypress(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onKeyPress:
            cb, cb_args, cb_kwargs = node._onKeyPress
            cb(e, *cb_args, **cb_kwargs)

    def flet(self, **kwargs):
        return self

    def textual(self, **kwargs):
        return self

    def tkinter(self, **kwargs):
        return self

    def qt(self, **kwargs):
        return self
