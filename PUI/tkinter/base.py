from .. import *
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import functools

class TPUIView(PUIView):
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
                self._after_id = parent.ui.after_idle(self._queued_sync)
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

class TkBaseWidget(PUINode):
    use_ttk = False
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
        if self.use_ttk:
            style_key = f'S{id(self.ui)}.{self.use_ttk}'
            style = ttk.Style(self.ui)
            if prev and prev.ui is not None:
                self.native_style = prev.native_style
            else:
                original_style = self.native_options.get('style') or self.use_ttk
                self.native_style = {key: style.lookup(original_style, key)
                                     for key in ('foreground', 'background', 'font')}
            style.configure(style_key,
                            foreground=self.native_style['foreground'] if self.style_color is None else f'#{self.style_color:06X}',
                            background=self.native_style['background'] if self.style_bgcolor is None else f'#{self.style_bgcolor:06X}',
                            font=self.font_spec() if any(value is not None for value in
                                (self.style_fontfamily, self.style_fontsize, self.style_fontweight)) else self.native_style['font'])
            self.ui.configure(style=style_key)
        else:
            for key, value in (('foreground', self.style_color), ('background', self.style_bgcolor)):
                if key in options:
                    self.ui.configure(**{key: self.native_options[key] if value is None else f'#{value:06X}'})
            if 'font' in options:
                customized = any(value is not None for value in
                                 (self.style_fontfamily, self.style_fontsize, self.style_fontweight))
                self.ui.configure(font=self.font_spec() if customized else self.native_options['font'])
        super().update(prev)

    def font_spec(self):
        default = tkFont.nametofont('TkDefaultFont', root=self.ui).actual()
        return (self.style_fontfamily if self.style_fontfamily is not None else default['family'],
                self.style_fontsize if self.style_fontsize is not None else default['size'],
                self.style_fontweight if self.style_fontweight is not None else default['weight'])
