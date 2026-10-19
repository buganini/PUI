from __future__ import annotations
from .. import _typing as _t
from .. import *
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
    expand_x1_children = 0
    expand_x2_children = 0
    expand_x3_children = 0
    expand_x4_children = 0
    expand_y1_children = 0
    expand_y2_children = 0
    expand_y3_children = 0
    expand_y4_children = 0
    cached_tparent = None

    @property
    def expand_x(self):
        parent = self.cached_tparent
        expand = self.expand_x_prio
        if not parent:
            return expand

        # textual handles 1fr as shrinkable, but we need scrolller's content not to shrink
        # See Exp.1 in refs/textual_layout.py
        if parent.scroll:
            return False

        # textual populates auto(1fr) to be 1fr(1fr), but we require expanding not to go over the container
        # See Exp.2 in refs/textual_layout.py
        if not parent.expand_x and expand < 3:
            return False

        return expand

    @property
    def expand_y(self):
        parent = self.cached_tparent
        expand = self.expand_y_prio
        if not parent:
            return expand

        # textual handles 1fr as shrinkable, but we need scrolller's content not to shrink
        # See Exp.1 in refs/textual_layout.py
        if parent.scroll:
            return False

        # textual populates auto(1fr) to be 1fr(1fr), but we require expanding not to go over the container
        # See Exp.2 in refs/textual_layout.py
        if not parent.expand_y and expand < 3:
            return False

        return expand

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
            setattr(self.ui.styles, name, None if value is None else f'#{value:06x}')
        weight = self.tstyle_fontweight
        self.ui.styles.text_style = (None if weight is None else
            'bold' if weight == 'bold' or isinstance(weight, (int, float)) and weight >= 600 else 'none')
        self.ui.styles.padding = self.tlayout_padding
        self.ui.styles.margin = self.tlayout_margin
        self.cached_tparent = parent = self.tparent
        if parent and self._visible:
            if self.tlayout_weight:
                if parent.container_x:
                    self.expand_x_prio = 4
                if parent.container_y:
                    self.expand_y_prio = 4

            if self.expand_x_prio >= 1:
                parent.expand_x1_children += 1
            if self.expand_x_prio >= 2:
                parent.expand_x2_children += 1
            if self.expand_x_prio >= 3:
                parent.expand_x3_children += 1
            if self.expand_x_prio >= 4:
                parent.expand_x4_children += 1

            if self.expand_y_prio >= 1:
                parent.expand_y1_children += 1
            if self.expand_y_prio >= 2:
                parent.expand_y2_children += 1
            if self.expand_y_prio >= 3:
                parent.expand_y3_children += 1
            if self.expand_y_prio >= 4:
                parent.expand_y4_children += 1

    def postUpdate(self):
        super().postUpdate()
        parent = self.cached_tparent
        if parent:
            if parent.container_x:
                if self.expand_x_prio < 1 and parent.expand_x1_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 2 and parent.expand_x2_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 3 and parent.expand_x3_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 4 and parent.expand_x4_children > 0:
                    self.expand_x_prio = 0

            if parent.container_y:
                if self.expand_y_prio < 1 and parent.expand_y1_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 2 and parent.expand_y2_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 3 and parent.expand_y3_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 4 and parent.expand_y4_children > 0:
                    self.expand_y_prio = 0

        self.t_update_layout()

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
        if self.tlayout_weight is not None and self.tlayout_weight > 0:
            parent = self.cached_tparent
            if parent and parent.container_x:
                width = f'{self.tlayout_weight}fr'
            if parent and parent.container_y:
                height = f'{self.tlayout_weight}fr'
        self.ui.styles.width = self.tlayout_width if self.tlayout_width is not None else width
        self.ui.styles.height = self.tlayout_height if self.tlayout_height is not None else height

class TPUIView(PUIView):
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
