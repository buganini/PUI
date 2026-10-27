from __future__ import annotations
from .. import _typing as _t
from .. import *
import asyncio
import threading
import flet as ft


def colour(value):
    if value is None:
        return None
    from ..color import rgba
    r, g, b, a = rgba(value)
    return f'#{r:02X}{g:02X}{b:02X}' if a == 255 else f'#{a:02X}{r:02X}{g:02X}{b:02X}'


class FView(PUIView):
    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    pui_virtual = True

    def __init__(self, *args):
        super().__init__(*args)
        self._redraw_lock = threading.Lock()

    def application(self):
        from .application import Application
        parent = self
        while parent is not None:
            if isinstance(parent, Application):
                return parent
            if parent.parent is parent:
                return None
            parent = parent.parent
        return None

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        app = self.application()
        with self._redraw_lock:
            self.dirty = True
            if self.updating or app is None or app.loop is None:
                return
            self.updating = True
        app.loop.call_soon_threadsafe(self.sync, context=app.context.copy())

    def sync(self):
        if self.retired_by or self.destroyed:
            return
        super().sync()
        app = self.application()
        if app is not None and app.ready:
            app.ui.update()

    def destroy(self, direct):
        self.destroyed = True
        self.dirty = self.updating = False
        super().destroy(direct)


class FBase(PUINode):
    def _observe_size(self):
        from .adaptive import observe
        return observe(self)

    def get_poster(self) -> _t.Poster:
        app = self.root.application()
        loop, context = app.loop, app.context
        from ..poster import make_poster
        return make_poster(
            lambda callback: loop.call_soon_threadsafe(callback, context=context.copy()),
            lambda delay, callback: loop.call_later(delay, callback, context=context.copy()))

    def __init__(self, *args):
        super().__init__(*args)
        self.child_weight = None
        parent = self.fparent
        if parent is not None:
            self.layout_weight = parent.child_weight
        self.flet_params = {}
        self.shell = None
        self.native_params = {}

    def flet(self: _t.NodeT, **kwargs: _t.Any) -> _t.NodeT:
        self.flet_params.update(kwargs)
        return self

    @property
    def outer(self):
        return self.shell if self.shell is not None else self.ui

    @property
    def fparent(self):
        parent = self.parent
        while parent is not None and parent is not self:
            if isinstance(parent, FBase):
                return parent
            if parent.parent is parent:
                break
            parent = parent.parent
        return None

    def update(self, prev):
        super().update(prev)
        self.native_params = prev.native_params if prev else {}
        for key, value in self.native_params.items():
            if key not in self.flet_params:
                setattr(self.ui, key, value)
        if not isinstance(self.ui, ft.Page):
            self.shell = prev.shell if prev and prev.shell is not None else ft.Container()
            self.shell.content = self.ui
            self.shell.visible = self._visible
            self.shell.expand = self.layout_weight
            self.shell.width = self._minimum_size('x')
            self.shell.height = self._minimum_size('y')
            self.shell.bgcolor = colour(self.style_bgcolor)
            self.shell.padding = self.padding(self.layout_padding)
            self.shell.margin = self.padding(self.layout_margin, ft.Margin)
            self.apply_style()
        for key, value in self.flet_params.items():
            if key not in self.native_params:
                self.native_params[key] = getattr(self.ui, key)
            setattr(self.ui, key, value)

    @staticmethod
    def padding(values, cls=ft.Padding):
        if values is None:
            return None
        top, right, bottom, left = values
        return cls(top=top, right=right, bottom=bottom, left=left)

    def apply_style(self):
        style = ft.TextStyle(size=self.style_fontsize,
                             font_family=self.style_fontfamily,
                             color=colour(self.style_color),
                             weight=ft.FontWeight(f'w{min(900, max(100, ((self.style_fontweight + 50) // 100) * 100))}')
                             if self.style_fontweight is not None else None)
        if isinstance(self.ui, ft.Text):
            self.ui.style = style
        elif isinstance(self.ui, (ft.TextField, ft.Dropdown)):
            self.ui.text_style = style
        elif isinstance(self.ui, ft.Checkbox):
            self.ui.label_style = style
        elif isinstance(self.ui, ft.RadioGroup):
            self.radio.label_style = style
        elif isinstance(self.ui, ft.DataTable):
            self.ui.data_text_style = style
            self.ui.heading_text_style = style
        elif isinstance(self.ui, ft.Button):
            self.ui.style = ft.ButtonStyle(text_style=style)
            self.ui.color = colour(self.style_color)
            self.ui.bgcolor = colour(self.style_bgcolor)

    def _preClicked(self):
        app = FView.application(self)
        if app is not None and app.focused_editor is not None:
            editor = app.focused_editor.get_node()
            if not editor.destroyed and editor.ui is not None:
                editor.on_change()
            else:
                app.focused_editor = None

    def releaseRetiredRefs(self):
        self.shell = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self.destroyed = True
        self.shell = None
        super().destroy(direct)
