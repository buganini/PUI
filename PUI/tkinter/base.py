from __future__ import annotations
from .. import _typing as _t
from .. import *
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import functools

class TPUIView(PUIView):
    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    pui_virtual = True

    def __init__(self, *args):
        super().__init__(*args)
        self._after_ui = None
        self._after_id = None

    def _queued_sync(self):
        self._after_id = self._after_ui = None
        self.sync()

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating or self._after_id is not None:
            return
        self.updating = True
        parent = self
        while parent is not None:
            if isinstance(parent.ui, tk.Misc):
                self._after_ui = parent.ui
                # Geometry idle flushes must not reenter reconciliation.
                self._after_id = parent.ui.after(0, self._queued_sync)
                return
            if parent.parent is parent:
                break
            parent = parent.parent
        self.sync()

    def destroy(self, direct):
        if self._after_id is not None:
            try:
                self._after_ui.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = self._after_ui = None
        self.destroyed = True
        self.dirty = self.updating = False
        if direct and self.ui is not None:
            try:
                self.ui.destroy()
            except tk.TclError:
                pass  # The native root may already have been closed.
        super().destroy(direct)

class _WindowCommands:
    """Workers only enqueue Python callbacks; all Tk calls stay on its thread."""
    def __init__(self, ui):
        from collections import deque
        from threading import Lock
        self.ui = ui
        self.pending = deque()
        self.lock = Lock()
        self.closed = False
        self.timer = ui.after(10, self._drain)

    def submit(self, callback):
        with self.lock:
            if self.closed:
                raise RuntimeError('Tk application has closed')
            self.pending.append(callback)

    def _drain(self):
        self.timer = None
        # Bound each batch so a busy producer cannot starve native events.
        for _ in range(256):
            with self.lock:
                if self.closed or not self.pending:
                    break
                callback = self.pending.popleft()
            try:
                callback()
            except Exception:
                import sys
                self.ui.report_callback_exception(*sys.exc_info())
        if not self.closed:
            self.timer = self.ui.after(10, self._drain)

    def close(self):
        with self.lock:
            self.closed = True
            self.pending.clear()
        if self.timer is not None:
            self.ui.after_cancel(self.timer)
            self.timer = None


class TkBaseWidget(PUINode):
    def _observe_size(self):
        from .adaptive import observe
        return observe(self)

    def get_poster(self) -> _t.Poster:
        app = self
        while app.parent is not app:
            app = app.parent
        if app._window_commands is None:
            app._window_commands = _WindowCommands(app.ui)
        from ..poster import make_poster
        import math
        return make_poster(app._window_commands.submit,
                           lambda delay, callback: app.ui.after(math.ceil(delay * 1000), callback))

    ttk_style = None
    pui_terminal = True
    def __init__(self, layout=None, side=None):
        super().__init__()
        self.layout_type = layout
        self.side = side

    @property
    def tkparent(self):
        parent = self.parent
        while parent is not None:
            if isinstance(parent, TkBaseWidget) or (isinstance(parent, TPUIView) and parent.ui is not None):
                return parent
            if parent is parent.parent:
                return None
            parent = parent.parent
        return None

    def destroy(self, direct):
        self.destroyed = True
        if direct and self.ui is not None:
            try:
                self.outer.destroy()
            except tk.TclError:
                pass
        super().destroy(direct)

    def update(self, prev):
        options = set(self.ui.keys())
        if prev and prev.ui is not None:
            self.native_options = prev.native_options
        else:
            self.native_options = {key: self.ui.cget(key) for key in
                                   ('width', 'height', 'foreground', 'background', 'font', 'style')
                                   if key in options}
        for key, value in (('width', self.layout_width), ('height', self.layout_height)):
            if key in options:
                self.ui.configure(**{key: self.native_options[key] if value is None else value})
        if self.ttk_style:
            # Leave unspecified options inherited from the theme. Copying lookup
            # results into an explicit style can bypass Aqua's native rendering.
            overrides = {}
            for key, value in (('foreground', self.style_color), ('background', self.style_bgcolor)):
                if value is not None:
                    option = 'fieldbackground' if self.ttk_style in ('TEntry', 'TCombobox') and key == 'background' else key
                    overrides[option] = f'#{value:06X}'
                    if self.ttk_style == 'Treeview' and key == 'background':
                        overrides['fieldbackground'] = overrides[option]
            if any(value is not None for value in
                   (self.style_fontfamily, self.style_fontsize, self.style_fontweight)):
                overrides['font'] = self.font_spec()
            original_style = self.native_options.get('style') or self.ttk_style
            # Separate option sets so removing an override restores inheritance,
            # including after a theme change, without leaving stale settings.
            mask = '_'.join(sorted(overrides)) or 'native'
            style_key = f'S{id(self.ui)}_{mask}.{original_style}'
            if overrides:
                ttk.Style(self.ui).configure(style_key, **overrides)
            self.ui.configure(style=style_key)
        else:
            self._apply_tk_colors()
            if self.ui.winfo_class() in ('Label', 'Canvas', 'Toplevel') and not hasattr(self.ui, '_pui_theme_binding'):
                self.ui._pui_theme_binding = self.ui.bind(
                    '<<ThemeChanged>>',
                    lambda event, widget=self.ui: widget.pui_node._apply_tk_colors()
                    if event.widget is widget else None, add='+')
            if 'font' in options:
                customized = any(value is not None for value in
                                 (self.style_fontfamily, self.style_fontsize, self.style_fontweight))
                self.ui.configure(font=self.font_spec() if customized else self.native_options['font'])
        self.ui.pui_node = self
        super().update(prev)

    def _apply_tk_colors(self):
        # Classic Tk widgets do not follow ttk themes on their own. In
        # particular, macOS may keep dark native labels beside light ttk frames.
        style = ttk.Style(self.ui)
        widget_class = self.ui.winfo_class()
        theme_class = {'Label': 'TLabel', 'Canvas': 'TFrame', 'Toplevel': 'TFrame'}.get(widget_class)
        for key, value in (('foreground', self.style_color), ('background', self.style_bgcolor)):
            if key not in self.native_options:
                continue
            color = self.native_options[key]
            if theme_class:
                color = style.lookup(theme_class, key) or color
            self.ui.configure(**{key: color if value is None else f'#{value:06X}'})

    def _preClicked(self):
        from .textfield import TextField
        focused = self.ui.focus_get()
        editor = getattr(focused, "pui_node", None)
        if isinstance(editor, TextField):
            editor.get_node().on_change()
            self.tkparent.ui.focus_set()

    def font_spec(self):
        default = tkFont.nametofont('TkDefaultFont', root=self.ui).actual()
        return (self.style_fontfamily if self.style_fontfamily is not None else default['family'],
                self.style_fontsize if self.style_fontsize is not None else default['size'],
                self.style_fontweight if self.style_fontweight is not None else default['weight'])
