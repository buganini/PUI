from .. import *
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import functools

class TPUIView(PUIView):
    def redraw(self):
        if self.ui:
            self.ui.after(0, functools.partial(self.update))
        else:
            self.update()

class TkBaseWidget(PUINode):
    use_ttk = False
    def __init__(self, layout=None, side=None):
        super().__init__()
        self.layout_type = layout
        self.side = side

    @property
    def tkparent(self):
        parent = self.parent
        while not isinstance(parent, TkBaseWidget):
            parent = parent.parent
            if parent==parent.parent:
                return None
        return parent

    def destroy(self, direct):
        if self.ui:
            self.ui.destroy() # tk's destroy
            self.ui = None

    def update(self, prev):
        if not self.layout_width is None:
            self.ui.configure(width=self.layout_width)
        if not self.layout_height is None:
            self.ui.configure(height=self.layout_height)

        if self.use_ttk:
            styleKey = f"S{id(self.ui)}.{self.use_ttk}"
            tkstyle = ttk.Style()
            if not self.style_color is None:
                tkstyle.configure(styleKey, foreground=f"#{self.style_color:06X}")
            if not self.style_bgcolor is None:
                tkstyle.configure(styleKey, background=f"#{self.style_bgcolor:06X}")
            if self.style_fontfamily or self.style_fontsize:
                default = tkFont.nametofont('TkDefaultFont').actual()
                font_family = self.style_fontfamily or default["family"]
                font_size = self.style_fontsize or default["size"]
                font_weight = self.style_fontweight or default["weight"]
                tkstyle.configure(styleKey, font=(font_family, font_size, font_weight))
            self.ui.configure(style=styleKey)
        else:
            if not self.style_color is None:
                self.ui.configure(fg=f"#{self.style_color:06X}")
            if not self.style_bgcolor is None:
                self.ui.configure(bg=f"#{self.style_bgcolor:06X}")
            if self.style_fontfamily or self.style_fontsize:
                default = tkFont.nametofont('TkDefaultFont').actual()
                font_family = self.style_fontfamily or default["family"]
                font_size = self.style_fontsize or default["size"]
                font_weight = self.style_fontweight or default["weight"]
                self.ui.configure(font=(font_family, font_size, font_weight))
        super().update(prev)