from __future__ import annotations
from .. import _typing as _t
from .. import *
from ..color import css_color
from textual import widgets, containers
from textual.app import App

class TBase(PUINode):
    _terminal_units = True
    def _observe_size(self):
        from .adaptive import observe
        return observe(self)

    def get_poster(self) -> _t.Poster:
        import asyncio
        import contextvars
        loop, context = asyncio.get_running_loop(), contextvars.copy_context()
        from ..poster import make_poster
        return make_poster(
            lambda callback: loop.call_soon_threadsafe(callback, context=context.copy()),
            lambda delay, callback: loop.call_later(delay, callback, context=context.copy()))

    scroll = False
    container_x = False # axis
    container_y = False # axis
    expand_x_prio = 0
    expand_y_prio = 0
    cached_tparent = None

    @property
    def _effective_weight(self):
        return self.layout_weight if self.tlayout_weight is None else self.tlayout_weight

    def _expands(self, axis):
        from ..expansion import priority, physical_children
        parent = self.cached_tparent
        value = priority(self, axis)
        if not parent:
            return value
        if parent.scroll:
            return False
        if getattr(parent, 'container_' + axis, False):
            highest = max((priority(child, axis, parent) for child in physical_children(parent)), default=0)
            if value < highest:
                return False
        if not getattr(parent, 'expand_' + axis) and value < 4:
            return False
        return value

    @property
    def expand_x(self):
        return self._expands('x')

    @property
    def expand_y(self):
        return self._expands('y')

    def tremove(self):
        self.ui.remove()

    def destroy(self, direct):
        if direct and self.ui is not None:
            self.ui.remove()
        super().destroy(direct)

    def update(self, prev):
        super().update(prev)

        if not self._visible or (prev is not None and not prev._visible):
            self.outer.display = self._visible
        for name, value in (('color', self.tstyle_color), ('background', self.tstyle_bgcolor)):
            setattr(self.ui.styles, name, None if value is None else css_color(value))
        weight = self.tstyle_fontweight
        self.ui.styles.text_style = (None if weight is None else
            'bold' if weight >= 600 else 'none')
        if prev is not None and (
            self.tstyle_color, self.tstyle_bgcolor, self.tstyle_fontweight
        ) != (prev.tstyle_color, prev.tstyle_bgcolor, prev.tstyle_fontweight):
            # Textual refreshes descendants after inline style changes, but their
            # cached visual styles only track their own CSS, not inherited CSS.
            for child in self.ui.walk_children():
                child.notify_style_update()
        self.ui.styles.padding = self.tlayout_padding
        self.ui.styles.margin = self.tlayout_margin
        self.cached_tparent = parent = self.tparent

    def postUpdate(self):
        super().postUpdate()
        self.t_update_layout()

    def postSync(self):
        super().postSync()
        from ..expansion import physical_children
        def refresh(node):
            if isinstance(node, TBase) and node.ui is not None:
                node.t_update_layout()
                for child in physical_children(node):
                    refresh(child)
        refresh(self)

    @property
    def tparent(self):
        parent = self.parent
        while not isinstance(parent, TBase):
            if parent==parent.parent:
                parent = None
                break
            parent = parent.parent
        return parent

    def t_update_layout(self):
        if not self.ui:
            return

        width = "auto"
        if self.expand_x:
            width = "1fr"

        height = "auto"
        if self.expand_y:
            height = "1fr"

        if self._debug:
            print("layout", self.key, f"{width}:{height} expand_x={self.expand_x}", f"expand_y={self.expand_y}", f"expand_x_prio={self.expand_x_prio}", f"expand_y_prio={self.expand_y_prio}")
        if self._effective_weight is not None and self._effective_weight > 0:
            parent = self.cached_tparent
            if parent and parent.container_x:
                width = f'{self._effective_weight}fr'
            if parent and parent.container_y:
                height = f'{self._effective_weight}fr'
        self.ui.styles.min_width = self._minimum_size('x')
        self.ui.styles.min_height = self._minimum_size('y')
        self.ui.styles.width = self.tlayout_width if self.tlayout_width is not None else width
        self.ui.styles.height = self.tlayout_height if self.tlayout_height is not None else height

class TPUIView(PUIView):
    def sync(self):
        app = self._textual_app()
        depth = getattr(app, '_pui_sync_depth', 0) if app is not None else 0
        if app is not None:
            app._pui_sync_depth = depth + 1
        try:
            result = super().sync()
            if depth == 0:
                # Sibling priorities are final only after reconciliation. Apply
                # sizes once, parent first, so compact ancestors constrain Scroll.
                def apply_sizes(node):
                    if isinstance(node, TBase):
                        node.t_update_layout()
                    for child in node.children:
                        apply_sizes(child)
                apply_sizes(self)
            return result
        finally:
            if app is not None:
                app._pui_sync_depth = depth

    _terminal_units = True
    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    pui_virtual = True

    def _textual_app(self):
        node = self
        while node is not None:
            if isinstance(getattr(node, 'ui', None), App):
                return node.ui
            parent = getattr(node, 'parent', None)
            if parent is node:
                break
            node = parent
        return None

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating:
            return
        app = self._textual_app()
        if app is None:
            return super().redraw()
        self.updating = True
        app.call_next(self._queued_sync)

    def _queued_sync(self):
        if self.retired_by or self.destroyed:
            self.updating = False
            return
        app = self._textual_app()
        if app is None:
            self.sync()
            return
        with app.batch_update():
            self.sync()
