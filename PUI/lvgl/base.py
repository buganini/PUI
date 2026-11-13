from __future__ import annotations
import heapq
import threading
import time
import traceback
from .. import _typing as _t
from .. import *
from ..color import rgba

from .native import ffi, lib

SEL = 0  # LV_PART_MAIN | LV_STATE_DEFAULT
_SPEC = lib.lv_pct(0)  # LV_COORD_TYPE_SPEC


def lv_color(value):
    r, g, b, a = rgba(value)
    return lib.lv_color_hex((r << 16) | (g << 8) | b), a


def is_pct(value):
    return bool(value & _SPEC) and (value & ~_SPEC) <= 1000


def grid_fr(weight):
    return lib.LV_COORD_MAX - 100 + max(1, min(100, int(weight)))


def text_bytes(value):
    return str(value).encode('utf-8')


# ---------------------------------------------------------------------------
# Runtime: everything native runs on the LVGL loop thread. Callbacks from
# LVGL never reconcile synchronously; redraws are queued like Qt's
# QueuedConnection so native objects are never deleted inside their events.
# ---------------------------------------------------------------------------

class _Runtime:
    def __init__(self):
        self.lock = threading.Lock()
        self.commands = []
        self.timers = []
        self.seq = 0
        self.pollers = []
        # > 0 while LVGL is calling into Python (inside lv_timer_handler).
        self.native_depth = 0

    def post(self, callback):
        with self.lock:
            self.commands.append(callback)

    def post_timer(self, delay, callback):
        with self.lock:
            self.seq += 1
            heapq.heappush(self.timers, (time.monotonic() + max(0, delay), self.seq, callback))

    def run_pending(self):
        """Run due work; repeats until nothing more is queued for now."""
        for _ in range(100):
            now = time.monotonic()
            with self.lock:
                work = self.commands
                self.commands = []
                while self.timers and self.timers[0][0] <= now:
                    work.append(heapq.heappop(self.timers)[2])
            if not work:
                return
            for callback in work:
                try:
                    callback()
                except Exception:
                    traceback.print_exc()

    def next_delay(self):
        with self.lock:
            if self.commands:
                return 0
            if self.timers:
                return max(0.0, self.timers[0][0] - time.monotonic())
        return None

    def poll(self):
        """Per-iteration hooks (pointer hover tracking)."""
        for poller in list(self.pollers):
            try:
                poller()
            except Exception:
                traceback.print_exc()

    def clear(self):
        with self.lock:
            self.commands.clear()
            self.timers.clear()


runtime = _Runtime()


class LPUIView(PUIView):
    pui_virtual = True

    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        runtime.post(self._queued_sync)

    def _queued_sync(self):
        if self.retired_by or self.destroyed:
            self.updating = False
            return
        self.sync()

    def destroy(self, direct):
        self.destroyed = True
        self.dirty = self.updating = False
        super().destroy(direct)


# ---------------------------------------------------------------------------
# Native observer: one per LVGL object, retained across declarations.
# ---------------------------------------------------------------------------

_natives = {}

_BASE_EVENTS = (lib.LV_EVENT_CLICKED, lib.LV_EVENT_DOUBLE_CLICKED)


class _Native:
    __slots__ = ('node', 'obj', 'handle', 'box_dims', 'store', 'size_observed', '__weakref__')

    def __init__(self, node, obj, events):
        self.node = node
        self.obj = obj
        self.box_dims = set()
        self.store = {}
        self.size_observed = False
        self.handle = ffi.new_handle(self)
        _natives[id(self)] = self
        lib.lv_obj_add_event_cb(obj, lib._pui_event_cb, lib.LV_EVENT_DELETE, self.handle)
        for code in set(_BASE_EVENTS + tuple(events)):
            lib.lv_obj_add_event_cb(obj, lib._pui_event_cb, code, self.handle)

    def listen(self, code):
        lib.lv_obj_add_event_cb(self.obj, lib._pui_event_cb, code, self.handle)


@ffi.def_extern()
def _pui_event_cb(e):
    try:
        native = ffi.from_handle(lib.lv_event_get_user_data(e))
    except Exception:
        return
    code = lib.lv_event_get_code(e)
    if code == lib.LV_EVENT_DELETE:
        if lib.lv_event_get_target_obj(e) != native.obj:
            return
        _natives.pop(id(native), None)
        for cleanup in native.store.pop('on_delete', ()):
            try:
                cleanup()
            except Exception:
                traceback.print_exc()
        node, native.node = native.node, None
        native.obj = None
        if node is not None and node._native is native:
            node.ui = None
        return
    node = native.node
    if node is None or node.destroyed or native.obj is None:
        return
    try:
        runtime.native_depth += 1
        try:
            node._lv_event(code, e)
        finally:
            runtime.native_depth -= 1
    except Exception:
        traceback.print_exc()


class LBaseWidget(PUINode):
    pui_terminal = True
    expand_x_prio = 0
    expand_y_prio = 0
    # Native size used when no explicit layout size is declared:
    # None keeps LVGL's class/theme default, 'content' or ('pct', n).
    _default_size = (None, None)
    _lv_events = ()
    _always_clickable = False

    def __init__(self):
        super().__init__()
        self._native = None
        self._applied = frozenset()

    # ---- hooks ----
    def create(self, parent):
        return lib.lv_obj_create(parent)

    def adopt(self, prev):
        """Take over per-native state from the retired declaration."""

    def configure(self, prev):
        """Apply this declaration's content to the native object."""

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_CLICKED:
            self._clicked(PUIEvent())
        elif code == lib.LV_EVENT_DOUBLE_CLICKED:
            self._dblclicked(PUIEvent())
        elif code == lib.LV_EVENT_SIZE_CHANGED:
            if self._native is not None and self._native.size_observed:
                _schedule_measure(self._native)

    # ---- tree ----
    @property
    def lv_parent_obj(self):
        parent = self.pui_dom_parent
        obj = None
        if parent is not None:
            obj = parent.get_node().inner
        return obj if obj is not None else lib.lv_screen_active()

    @property
    def inner(self):
        return self.ui

    @property
    def outer(self):
        return self.ui

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.lv_obj_move_to_index(child.outer, idx)

    def removeChild(self, idx, child):
        # Keep native indices of remaining siblings aligned with DOM offsets
        # until the removed subtree is deleted.
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.lv_obj_move_to_index(child.outer, -1)

    def get_poster(self) -> _t.Poster:
        from ..poster import make_poster
        return make_poster(runtime.post, runtime.post_timer)

    def _preClicked(self):
        from .textfield import commit_focused
        commit_focused(self)

    def _invoke_callback(self, callback, *args, **kwargs):
        # Run application callbacks after the native event returns, outside
        # lv_timer_handler: they may redraw, delete this object, or open a
        # blocking dialog that runs its own event loop.
        runtime.post(lambda: callback(*args, **kwargs))

    def _base_expansion_priority(self, axis):
        return self.expand_x_prio if axis == 'x' else self.expand_y_prio

    # ---- lifecycle ----
    def update(self, prev):
        if prev is not None and prev.ui is not None and prev._native is not None and prev._native.obj is not None:
            self.ui = prev.ui
            self._native = prev._native
            self._applied = prev._applied
            self.adopt(prev)
        else:
            self.ui = self.create(self.lv_parent_obj)
            self._native = _Native(self, self.ui, self._lv_events)
            self._applied = frozenset()
        self._native.node = self
        for prop in self._applied:
            lib.lv_obj_remove_local_style_prop(self.ui, prop, SEL)
        self.configure(prev)
        self._apply_styles()
        super().update(prev)

    def destroy(self, direct):
        native = self._native
        if native is not None:
            native.node = None
            if direct and native.obj is not None:
                lib.lv_obj_delete(native.obj)
        self._native = None
        self.ui = None
        super().destroy(direct)

    def releaseRetiredRefs(self):
        super().releaseRetiredRefs()
        self._native = None

    # ---- sizing ----
    def _set_dim(self, horizontal, value):
        setter = lib.lv_obj_set_width if horizontal else lib.lv_obj_set_height
        prop = lib.LV_STYLE_WIDTH if horizontal else lib.LV_STYLE_HEIGHT
        if value is None:
            lib.lv_obj_remove_local_style_prop(self.ui, prop, SEL)
        elif value == 'content':
            setter(self.ui, lib.LV_SIZE_CONTENT)
        elif isinstance(value, tuple):
            setter(self.ui, lib.lv_pct(value[1]))
        else:
            setter(self.ui, int(value))

    def _apply_dim(self, horizontal):
        explicit = self.layout_width if horizontal else self.layout_height
        self._set_dim(horizontal, explicit if explicit is not None
                      else self._default_size[0 if horizontal else 1])
        self._native.box_dims.discard('w' if horizontal else 'h')

    def _apply_styles(self):
        obj = self.ui
        applied = set()
        self._apply_dim(True)
        self._apply_dim(False)
        minimum = self._minimum_size('x')
        if minimum is not None:
            lib.lv_obj_set_style_min_width(obj, int(minimum), SEL)
            applied.add(lib.LV_STYLE_MIN_WIDTH)
        minimum = self._minimum_size('y')
        if minimum is not None:
            lib.lv_obj_set_style_min_height(obj, int(minimum), SEL)
            applied.add(lib.LV_STYLE_MIN_HEIGHT)
        if self.layout_padding is not None:
            top, right, bottom, left = self.layout_padding
            lib.lv_obj_set_style_pad_top(obj, int(top), SEL)
            lib.lv_obj_set_style_pad_right(obj, int(right), SEL)
            lib.lv_obj_set_style_pad_bottom(obj, int(bottom), SEL)
            lib.lv_obj_set_style_pad_left(obj, int(left), SEL)
            applied.update((lib.LV_STYLE_PAD_TOP, lib.LV_STYLE_PAD_RIGHT,
                            lib.LV_STYLE_PAD_BOTTOM, lib.LV_STYLE_PAD_LEFT))
        if self.layout_margin is not None:
            top, right, bottom, left = self.layout_margin
            lib.lv_obj_set_style_margin_top(obj, int(top), SEL)
            lib.lv_obj_set_style_margin_right(obj, int(right), SEL)
            lib.lv_obj_set_style_margin_bottom(obj, int(bottom), SEL)
            lib.lv_obj_set_style_margin_left(obj, int(left), SEL)
            applied.update((lib.LV_STYLE_MARGIN_TOP, lib.LV_STYLE_MARGIN_RIGHT,
                            lib.LV_STYLE_MARGIN_BOTTOM, lib.LV_STYLE_MARGIN_LEFT))
        if self.style_color is not None:
            color, opa = lv_color(self.style_color)
            lib.lv_obj_set_style_text_color(obj, color, SEL)
            lib.lv_obj_set_style_text_opa(obj, opa, SEL)
            applied.update((lib.LV_STYLE_TEXT_COLOR, lib.LV_STYLE_TEXT_OPA))
        if self.style_bgcolor is not None:
            color, opa = lv_color(self.style_bgcolor)
            lib.lv_obj_set_style_bg_color(obj, color, SEL)
            lib.lv_obj_set_style_bg_opa(obj, opa, SEL)
            applied.update((lib.LV_STYLE_BG_COLOR, lib.LV_STYLE_BG_OPA))
        if self.style_fontsize is not None or self.style_fontweight is not None:
            # Only the bundled Montserrat faces exist (regular sizes 8-48,
            # bold 14/28); fontFamily cannot select other fonts.
            from .font import resolve
            lib.lv_obj_set_style_text_font(obj, resolve(obj, self.style_fontsize, self.style_fontweight), SEL)
            applied.add(lib.LV_STYLE_TEXT_FONT)
        self._applied = frozenset(applied)

        if self._always_clickable or self._onClicked or self._onDblClicked:
            lib.lv_obj_add_flag(obj, lib.LV_OBJ_FLAG_CLICKABLE)
        else:
            lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_CLICKABLE)
        if self._visible:
            lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_HIDDEN)
        else:
            lib.lv_obj_add_flag(obj, lib.LV_OBJ_FLAG_HIDDEN)

    # ---- size observation (adaptive layouts) ----
    def _observe_size(self):
        native = self._native
        if native is None or native.obj is None:
            return None
        if not native.size_observed:
            native.size_observed = True
            native.listen(lib.LV_EVENT_SIZE_CHANGED)
        _schedule_measure(native)

        def close():
            native.size_observed = False
        return close


_measure_pending = set()


def _schedule_measure(native):
    key = id(native)
    if key in _measure_pending:
        return
    _measure_pending.add(key)

    def measure():
        _measure_pending.discard(key)
        node = native.node
        if node is None or native.obj is None or not native.size_observed:
            return
        lib.lv_obj_update_layout(native.obj)
        node._set_size(lib.lv_obj_get_content_width(native.obj),
                       lib.lv_obj_get_content_height(native.obj))
    runtime.post(measure)


# ---------------------------------------------------------------------------
# Layout helpers shared by boxes, windows and scroll areas.
# ---------------------------------------------------------------------------

def physical_children(node, include_hidden=True):
    for child in node.children:
        child = child.get_node()
        if child.pui_outoforder:
            continue
        if child.pui_virtual:
            yield from physical_children(child, include_hidden)
        elif isinstance(child, LBaseWidget) and child.ui is not None:
            if include_hidden or child._visible:
                yield child


def fills_axis(obj, horizontal):
    """Whether obj's size on an axis is decided by its parent, not its content."""
    size = lib.lv_obj_get_style_width(obj, SEL) if horizontal else lib.lv_obj_get_style_height(obj, SEL)
    if size != lib.LV_SIZE_CONTENT:
        return True
    # A content-sized child of a Scroll's disabled axis is at least as large
    # as the viewport (min 100%), so its allocation comes from the parent.
    minimum = lib.lv_obj_get_style_min_width(obj, SEL) if horizontal else lib.lv_obj_get_style_min_height(obj, SEL)
    if is_pct(minimum):
        return True
    owner = lib.lv_obj_get_parent(obj)
    if owner == ffi.NULL:
        return False
    layout = lib.lv_obj_get_style_layout(owner, SEL)
    if layout == lib.LV_LAYOUT_FLEX and lib.lv_obj_get_style_flex_grow(obj, SEL) > 0:
        row = (lib.lv_obj_get_style_flex_flow(owner, SEL) & lib.LV_FLEX_COLUMN) == 0
        if row == horizontal:
            return True
    if layout == lib.LV_LAYOUT_GRID:
        align = (lib.lv_obj_get_style_grid_cell_x_align(obj, SEL) if horizontal
                 else lib.lv_obj_get_style_grid_cell_y_align(obj, SEL))
        if align == lib.LV_GRID_ALIGN_STRETCH:
            return True
    return False


def force_dim(child, horizontal, pct=100):
    (lib.lv_obj_set_width if horizontal else lib.lv_obj_set_height)(child.outer, lib.lv_pct(pct))
    child._native.box_dims.add('w' if horizontal else 'h')


def release_dim(child, horizontal):
    key = 'w' if horizontal else 'h'
    if key in child._native.box_dims:
        child._apply_dim(horizontal)


def configure_flex(owner, horizontal, fill_main=None, fill_cross=None):
    """Distribute an LVGL flex container like the other PUI backends.

    Children with the highest expansion priority on the main axis grow by
    their weight; children that expand on the cross axis fill it.
    """
    from ..expansion import priority
    obj = owner.inner
    if obj is None:
        return
    main = fills_axis(obj, horizontal) if fill_main is None else fill_main
    cross = fills_axis(obj, not horizontal) if fill_cross is None else fill_cross
    axis, other = ('x', 'y') if horizontal else ('y', 'x')
    children = list(physical_children(owner))
    prios = [priority(child, axis, owner) for child in children]
    highest = max((p for child, p in zip(children, prios) if child._visible), default=0)
    growing = [main and child._visible and highest > 0 and p == highest
               for child, p in zip(children, prios)]
    weights = [max(1, child.layout_weight or 1) for child in children]
    top = max((w for w, g in zip(weights, growing) if g), default=1)
    if top > 255:
        weights = [max(1, round(w * 255 / top)) for w in weights]
    for child, grows, weight in zip(children, growing, weights):
        native = child.outer
        lib.lv_obj_set_flex_grow(native, weight if grows else 0)
        main_size = lib.lv_obj_get_style_width(native, SEL) if horizontal else lib.lv_obj_get_style_height(native, SEL)
        if not grows and is_pct(main_size):
            if ('w' if horizontal else 'h') in child._native.box_dims:
                release_dim(child, horizontal)
            elif (child.layout_width if horizontal else child.layout_height) is None:
                (lib.lv_obj_set_width if horizontal else lib.lv_obj_set_height)(native, lib.LV_SIZE_CONTENT)
        explicit_cross = child.layout_height if horizontal else child.layout_width
        if cross and explicit_cross is None and priority(child, other, owner) > 0:
            force_dim(child, not horizontal)
        else:
            release_dim(child, not horizontal)
        lib.lv_obj_mark_layout_as_dirty(native)
    # A child box may now fill a different set of axes.
    for child in children:
        hook = getattr(child, '_relayout', None)
        if hook is not None:
            hook()


@ffi.def_extern()
def _pui_anim_busy_cb(var, start):
    obj = ffi.cast('lv_obj_t *', var)
    lib.lv_bar_set_start_value(obj, 0, lib.LV_ANIM_OFF)
    lib.lv_bar_set_value(obj, start + 25, lib.LV_ANIM_OFF)
    lib.lv_bar_set_start_value(obj, start, lib.LV_ANIM_OFF)
