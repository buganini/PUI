from __future__ import annotations
from . import _typing as _t
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
    _terminal_units = False
    tlayout_width = tlayout_height = tlayout_weight = None
    tlayout_padding = tlayout_margin = None
    tstyle_color = tstyle_bgcolor = tstyle_fontweight = None

    # Tell DOM syncer not to go deeper into the node, it should be True for non-container elements
    pui_terminal = False

    # Keep existing children without reconciling or mounting new children.
    pui_frozen: bool = False

    # Menu and window-like UI elements, are out-of-order, so they are moved to the end of siblings before DOM syncing to simplify the process
    pui_outoforder = False

    # When enabled, children are added in reverse order, used by Stack
    pui_reversed_order = False

    # Used by PUIView
    pui_isview = False

    # Used by TimelineView, TabView, Sub-View or other nodes don't link to a real UI hierarchy
    # Children of virtual nodes will be promoted to the same level as the virtual node, addChild/removeChild won't be called for virtual nodes
    pui_virtual = False

    # When disabled, children are not allowed to be moved when DOM syncing, QSpacerItem is an example of non-movable node
    pui_movable = True

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
        self._ref = None
        self._tag = ""

        self._state = None
        self._size_started = False
        self._size_cleanup = None
        self._size_refresh = None
        self._visible = True
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
        self._onMouseEnter = None
        self._onMouseLeave = None
        self._onWheel = None
        self._onDragEntered = None
        self._onDropped = None
        self._drop_extensions = None

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
        self._dom_offset_version = object()
        self._dom_offset_cache = None

        if self.parent is self:
            self._path = tuple()
        else:
            self._path = self.parent._path + tuple([len(self.parent.children)])
            self.parent.children.append(self)

        # print(type(self).__name__, self._path, "parent=", self.parent._path)

    def findDomOffsetForNode(self, node):
        cache = node._dom_offset_cache
        if cache is not None and cache[0] is self._dom_offset_version:
            return cache[1]
        result = self._findDomOffsetForNode(node)
        if result[0]:
            # The unique version token also identifies the parent, without
            # retaining that parent through the target's cache.
            node._dom_offset_cache = (self._dom_offset_version, result)
        return result

    def _findDomOffsetForNode(self, node):
        if self is node:
            return True, 0
        offset = 0
        for c in self.children:
            if c is node:
                return True, offset
            if c.pui_virtual:
                found, off = c._findDomOffsetForNode(node)
                offset += off
                if found:
                    return True, offset
            elif not c.pui_outoforder:
                offset += 1
        return False, offset

    def _is_frozen(self):
        node = self
        while node is not None:
            node = node.get_node()
            if node.pui_frozen:
                return True
            parent = node.parent
            if parent is node:
                break
            node = parent
        return False

    def genKey(self):
        # Keep the path relative to PUIView for independent subview updates.
        names = [node.name or type(node).__name__ for node in self.root.frames]
        names.append(self.name or type(self).__name__)
        key = "|".join(names)
        if self.grid_row is not None and self.grid_column is not None:
            key += f":grid:{self.grid_row},{self.grid_column},{self.grid_rowspan},{self.grid_columnspan}"
        if hasattr(self, "_internal_tag"):
            key += f"#tag={self._internal_tag}"
        if self._id:
            key += f"#id={self._id}"
        if self._ref is not None:
            key += f"#ref={self._ref}"
        self.key = key

    def ref(self: _t.NodeT, name: str) -> _t.NodeT:
        if not isinstance(name, str) or not name:
            raise ValueError("ref name must be a nonempty string")
        self._ref = name
        self.genKey()
        return self

    def __pui_binder__(self):
        from .refs import NodeBinder
        return NodeBinder(self)

    def __enter__(self: _t.NodeT) -> _t.NodeT:
        # print("enter", type(self).__name__, id(self))
        self.root.frames.append(self)
        return self

    def __exit__(self, ex_type: _t.Any, value: _t.Any, traceback: _t.Any) -> _t.Any:
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
            if prev._state is not None:
                self._state = prev._state
                self._size_started = prev._size_started
                self._size_cleanup, prev._size_cleanup = prev._size_cleanup, None
                self._size_refresh, prev._size_refresh = prev._size_refresh, None
        if prev and prev is not self:
            prev.retired_by = self

    def releaseRetiredRefs(self):
        self._dom_offset_cache = None
        self.root = None
        self.parent = None
        self.children = tuple()
        self.ui = None
        self.pui_dom_parent = None
        self.args = tuple()

        self._onChanged = None
        self._onClicked = None
        self._onDblClicked = None
        self._onInput = None
        self._onKeyPress = None
        self._onMouseDown = None
        self._onMouseUp = None
        self._onMouseMove = None
        self._onMouseEnter = None
        self._onMouseLeave = None
        self._onWheel = None
        self._onDragEntered = None
        self._onDropped = None
        self._drop_extensions = None

    def postUpdate(self):
        if self._state is not None:
            self._start_size()
            if self._size_refresh is not None:
                self._size_refresh()

    def _observe_size(self):
        return None

    def _start_size(self):
        if not self._size_started and not self.destroyed and self.ui is not None:
            self._size_started = True
            self._size_cleanup = self._observe_size()

    def _set_size(self, width, height):
        node = self.get_node()
        if not node.destroyed and node._state is not None:
            # State handles equality checks and subscriptions from content().
            node._state.size = (max(0, width), max(0, height))

    def _ensure_size(self):
        from types import SimpleNamespace
        from .state import State
        self.root._has_size_observers = True
        if self._state is None:
            candidates = getattr(self.root, '_previous_size_nodes', {}).get(self.key, ())
            previous = (candidates[0] if len(candidates) == 1 else
                        next((n for n in candidates if n._path == self._path), None))
            if previous is not None and previous._state is not None:
                self._state = previous._state
            else:
                self._state = State(SimpleNamespace(size=None))

    def size(self) -> _t.Binding[tuple[float, float] | None]:
        """Observe this container's content size; None until native layout completes."""
        if self._terminal_units:
            from .state import DummyBinding
            return DummyBinding(None)
        return self._size_binding()

    def tsize(self) -> _t.Binding[tuple[float, float] | None]:
        """Observe Textual content size in cells; other backends return None."""
        if not self._terminal_units:
            from .state import DummyBinding
            return DummyBinding(None)
        return self._size_binding()

    def _size_binding(self):
        node = self.get_node()
        node._ensure_size()
        node._start_size()
        return node._state('size')

    def preSync(self):
        pass

    def postSync(self):
        pass

    def destroy(self, direct):
        from .refs import ref_clear
        ref_clear(self)
        if self._size_cleanup is not None:
            self._size_cleanup()
            self._size_cleanup = None
        self._size_refresh = None
        self.destroyed = True
        self.root = None
        self.parent = None
        self.children = tuple()
        self.ui = None
        self.layout = None
        self.pui_dom_parent = None

        self._onChanged = None
        self._onClicked = None
        self._onDblClicked = None
        self._onInput = None
        self._onKeyPress = None
        self._onMouseDown = None
        self._onMouseUp = None
        self._onMouseMove = None
        self._onMouseEnter = None
        self._onMouseLeave = None
        self._onWheel = None
        self._onDragEntered = None
        self._onDropped = None
        self._drop_extensions = None

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def debug(self: _t.NodeT, level: int = 1) -> _t.NodeT:
        self._debug = level
        return self

    def id(self: _t.NodeT, name: _t.Any) -> _t.NodeT:
        self._id = name
        self.genKey()
        return self

    def tag(self: _t.NodeT, tag: _t.Any) -> _t.NodeT:
        self._tag = tag
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
            headline.append(" # Tag:  ")
            headline.append(self._tag)

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

    def layout(
        self: _t.NodeT,
        width: _t.Number | None = None,
        height: _t.Number | None = None,
        weight: _t.Number | None = None,
        padding: _t.Insets | None = None,
        margin: _t.Insets | None = None,
    ) -> _t.NodeT:
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

    def tlayout(
        self: _t.NodeT, width: int | None = None, height: int | None = None,
        weight: _t.Number | None = None, padding: int | _t.Sequence[int] | None = None,
        margin: int | _t.Sequence[int] | None = None,
    ) -> _t.NodeT:
        """Textual layout in terminal cells; ignored by graphical backends."""
        if self._terminal_units:
            if width is not None:
                self.tlayout_width = width
            if height is not None:
                self.tlayout_height = height
            if weight is not None:
                self.tlayout_weight = weight
            if padding is not None:
                self.tlayout_padding = trbl(padding)
            if margin is not None:
                self.tlayout_margin = trbl(margin)
        return self

    def tstyle(
        self: _t.NodeT, color: int | None = None, bgColor: int | None = None,
        fontWeight: str | int | None = None,
    ) -> _t.NodeT:
        """Textual colors and normal/bold weight; the terminal controls its font."""
        if self._terminal_units:
            if color is not None:
                self.tstyle_color = color
            if bgColor is not None:
                self.tstyle_bgcolor = bgColor
            if fontWeight is not None:
                self.tstyle_fontweight = fontWeight
        return self

    def _wide_matches(self, minWidth, terminal):
        if self._terminal_units != terminal:
            return False
        from .adaptive import matches
        parent = self.parent
        while parent is not None and parent.pui_virtual and parent.parent is not parent:
            parent = parent.parent
        if parent is None or parent is self:
            return False
        parent._ensure_size()
        parent._start_size()
        return matches(parent._state.size, (minWidth, None, None, None))

    def wideLayout(
        self: _t.NodeT, minWidth: _t.Number, *,
        width: _t.Number | None = None,
        height: _t.Number | None = None,
        weight: _t.Number | None = None,
        padding: _t.Insets | None = None,
        margin: _t.Insets | None = None,
    ) -> _t.NodeT:
        """Apply layout overrides when the parent reaches minWidth; later calls win."""
        if self._wide_matches(minWidth, False):
            self.layout(width=width, height=height, weight=weight, padding=padding, margin=margin)
        return self

    def wideStyle(
        self: _t.NodeT, minWidth: _t.Number, *,
        color: int | None = None,
        bgColor: int | None = None,
        fontSize: _t.Number | None = None,
        fontWeight: str | int | None = None,
        fontFamily: str | None = None,
    ) -> _t.NodeT:
        """Apply style overrides when the parent reaches minWidth; later calls win."""
        if self._wide_matches(minWidth, False):
            self.style(color=color, bgColor=bgColor, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily)
        return self

    def tWideLayout(
        self: _t.NodeT, minWidth: int, *,
        width: int | None = None,
        height: int | None = None,
        weight: _t.Number | None = None,
        padding: int | _t.Sequence[int] | None = None,
        margin: int | _t.Sequence[int] | None = None,
    ) -> _t.NodeT:
        """Apply tlayout overrides when the parent reaches minWidth; later calls win."""
        if self._wide_matches(minWidth, True):
            self.tlayout(width=width, height=height, weight=weight, padding=padding, margin=margin)
        return self

    def tWideStyle(
        self: _t.NodeT, minWidth: int, *,
        color: int | None = None,
        bgColor: int | None = None,
        fontWeight: str | int | None = None,
    ) -> _t.NodeT:
        """Apply tstyle overrides when the parent reaches minWidth; later calls win."""
        if self._wide_matches(minWidth, True):
            self.tstyle(color=color, bgColor=bgColor, fontWeight=fontWeight)
        return self

    def visible(
        self: _t.NodeT, value: bool = True, *,
        minWidth: _t.Number | None = None, maxWidth: _t.Number | None = None,
        minHeight: _t.Number | None = None, maxHeight: _t.Number | None = None,
        tMinWidth: int | None = None, tMaxWidth: int | None = None,
        tMinHeight: int | None = None, tMaxHeight: int | None = None,
    ) -> _t.NodeT:
        """Show within the parent's content-size bounds (inclusive min, exclusive max)."""
        from .adaptive import matches
        limits = ((tMinWidth, tMaxWidth, tMinHeight, tMaxHeight) if self._terminal_units
                  else (minWidth, maxWidth, minHeight, maxHeight))
        self._visible = bool(value)
        if any(v is not None for v in limits):
            parent = self.parent
            while parent is not None and parent.pui_virtual and parent.parent is not parent:
                parent = parent.parent
            if parent is not None and parent is not self:
                parent._ensure_size()
                parent._start_size()
                self._visible = bool(value) and matches(parent._state.size, limits)
            else:
                self._visible = False
        self.pui_frozen = not self._visible
        return self

    def style(
        self: _t.NodeT,
        color: int | None = None,
        bgColor: int | None = None,
        fontSize: _t.Number | None = None,
        fontWeight: str | int | None = None,
        fontFamily: str | None = None,
    ) -> _t.NodeT:
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

    def grid(
        self: _t.NodeT,
        row: int | None = None,
        column: int | None = None,
        rowspan: int | None = None,
        columnspan: int | None = None,
    ) -> _t.NodeT:
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

    def dragEnter(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onDragEntered = callback, cb_args, cb_kwargs
        return self

    def drop(
        self: _t.NodeT,
        callback: _t.Callback,
        *cb_args: _t.Any,
        extensions: str | _t.Iterable[str] | None = None,
        **cb_kwargs: _t.Any,
    ) -> _t.NodeT:
        from .drop import extensions as normalize_extensions
        self._drop_extensions = normalize_extensions(extensions)
        self._onDropped = callback, cb_args, cb_kwargs
        return self

    def click(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onClicked = callback, cb_args, cb_kwargs
        return self

    def _preClicked(self):
        pass

    def _clicked(self, e=None, *args, **kwargs):
        node = self.get_node()
        node._preClicked()
        if node._onClicked:
            cb, cb_args, cb_kwargs = node._onClicked
            cb(e, *cb_args, **cb_kwargs)

    def dblclick(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onDblClicked = callback, cb_args, cb_kwargs
        return self

    def _dblclicked(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onDblClicked:
            cb, cb_args, cb_kwargs = node._onDblClicked
            cb(e, *cb_args, **cb_kwargs)

    def change(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onChanged = callback, cb_args, cb_kwargs
        return self

    def _change(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onChanged:
            cb, cb_args, cb_kwargs = node._onChanged
            cb(e, *cb_args, **cb_kwargs)

    def input(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onInput = callback, cb_args, cb_kwargs
        return self

    def _input(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onInput:
            cb, cb_args, cb_kwargs = node._onInput
            cb(e, *cb_args, **cb_kwargs)

    def mousedown(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onMouseDown = callback, cb_args, cb_kwargs
        return self

    def _mousedown(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseDown:
            cb, cb_args, cb_kwargs = node._onMouseDown
            cb(e, *cb_args, **cb_kwargs)

    def mouseup(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onMouseUp = callback, cb_args, cb_kwargs
        return self

    def _mouseup(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseUp:
            cb, cb_args, cb_kwargs = node._onMouseUp
            cb(e, *cb_args, **cb_kwargs)

    def mousemove(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onMouseMove = callback, cb_args, cb_kwargs
        return self

    def _mousemove(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseMove:
            cb, cb_args, cb_kwargs = node._onMouseMove
            cb(e, *cb_args, **cb_kwargs)

    def mouseenter(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onMouseEnter = callback, cb_args, cb_kwargs
        return self

    def _mouseenter(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseEnter:
            cb, cb_args, cb_kwargs = node._onMouseEnter
            cb(e, *cb_args, **cb_kwargs)

    def mouseleave(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onMouseLeave = callback, cb_args, cb_kwargs
        return self

    def _mouseleave(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onMouseLeave:
            cb, cb_args, cb_kwargs = node._onMouseLeave
            cb(e, *cb_args, **cb_kwargs)

    def wheel(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onWheel = callback, cb_args, cb_kwargs
        return self

    def _wheel(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onWheel:
            cb, cb_args, cb_kwargs = node._onWheel
            cb(e, *cb_args, **cb_kwargs)

    def keypress(self: _t.NodeT, callback: _t.Callback, *cb_args: _t.Any, **cb_kwargs: _t.Any) -> _t.NodeT:
        self._onKeyPress = callback, cb_args, cb_kwargs
        return self

    def _keypress(self, e, *args, **kwargs):
        node = self.get_node()
        if node._onKeyPress:
            cb, cb_args, cb_kwargs = node._onKeyPress
            cb(e, *cb_args, **cb_kwargs)

    def flet(self: _t.NodeT, **kwargs: _t.Any) -> _t.NodeT:
        return self

    def textual(self: _t.NodeT, **kwargs: _t.Any) -> _t.NodeT:
        return self

    def tkinter(self: _t.NodeT, **kwargs: _t.Any) -> _t.NodeT:
        return self

    def qt(self: _t.NodeT, **kwargs: _t.Any) -> _t.NodeT:
        return self
