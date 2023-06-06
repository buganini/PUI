from .. import *
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont

class TkBaseWidget(PUINode):
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
        if not self.style_color is None:
            self.ui.configure(fg=f"#{self.style_color:06X}")
        if not self.style_bgcolor is None:
            self.ui.configure(bg=f"#{self.style_bgcolor:06X}")
        if self.style_fontfamily or self.style_fontsize:
            print(self.key, self.style_fontfamily, self.style_fontsize)
            default = tkFont.nametofont('TkDefaultFont').actual()
            font_family = self.style_fontfamily or default["family"]
            font_size = self.style_fontsize or default["size"]
            font_weight = self.style_fontweight or default["weight"]
            self.ui.configure(font=(font_family, font_size, font_weight))
        super().update(prev)