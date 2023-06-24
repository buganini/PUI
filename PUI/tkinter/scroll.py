from .. import *
from .base import *
import math

class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        self.vertical = None
        self.horizontal = False

        self.container = ttk.Frame(parent)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.scroll_y = tk.Scrollbar(self.container, orient=tk.VERTICAL)
        self.scroll_x = tk.Scrollbar(self.container, orient=tk.HORIZONTAL)
        self.should_scroll_y = False
        self.should_scroll_x = False
        self.last_bbox = None
        self.last_scroll_x = None
        self.last_scroll_y = None

        self.canvas = tk.Canvas(self.container)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        super().__init__(self.canvas)
        self.canvas.create_window(0, 0, window=self, anchor="nw")

        self.bind("<Configure>", self._on_configure)

    def set_scroll(self, vertical, horizontal):
        self.vertical = vertical
        self.horizontal = horizontal

        self.update_scroller()

    def grid(self, *args, **kwargs):
        self.container.grid(*args, **kwargs)

    def configure(self, *args, **kwargs):
        self.container.configure(*args, **kwargs)

    def _on_configure(self, event):
        self.update_scroller()

    def update_scroller(self):
        bbox = self.canvas.bbox("all")
        _, _, w, h = bbox
        self.canvas.configure(scrollregion=bbox)
        if self.horizontal is False:
            self.canvas.configure(width=w)
        if self.vertical is False:
            self.canvas.configure(height=h)

        self.should_scroll_y = self.vertical or (self.vertical is None and h > self.canvas.winfo_height())
        if self.should_scroll_y:
            self.scroll_y.config(command=self.canvas.yview)
            self.canvas.config(yscrollcommand=self._on_scroll_y)
            self.scroll_y.grid(row=0, column=1, sticky="ns")

            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_y)
            self.canvas.bind("<Button-4>", self._on_mousewheel_y)
            self.canvas.bind("<Button-5>", self._on_mousewheel_y)
        else:
            self.scroll_y.grid_forget()

        self.should_scroll_x = self.horizontal or (self.horizontal is None and w > self.canvas.winfo_width())
        if self.should_scroll_x:
            self.scroll_x.config(command=self.canvas.xview)
            self.canvas.config(xscrollcommand=self._on_scroll_x)
            self.scroll_x.grid(row=1, column=0, sticky="ew")
        else:
            self.scroll_x.grid_forget()

    def _on_scroll_x(self, first, last):
        self.scroll_x.set(first, last)
        bbox = self.canvas.bbox("all")
        if self.last_bbox == bbox and self.last_scroll_x != (first,last):
            if float(first) < 0.05:
                self.puinode.align_x = 0
            elif float(last) > 0.95:
                self.puinode.align_x = 1
        else:
            self.last_bbox = bbox
            self.last_scroll_x = (first,last)

    def _on_scroll_y(self, first, last):
        self.scroll_y.set(first, last)
        bbox = self.canvas.bbox("all")
        if self.last_bbox == bbox and self.last_scroll_y != (first,last):
            if float(first) < 0.05:
                self.puinode.align_y = 0
            elif float(last) > 0.95:
                self.puinode.align_y = 1
        else:
            self.last_bbox = bbox
            self.last_scroll_y = (first,last)

    def _on_mousewheel_y(self, event):
        if not self.should_scroll_y:
            return
        if event.num == 5:
            delta = 1
        elif event.num == 4:
            delta = -1
        elif event.delta > 0:
            delta = 1
        elif event.delta < 0:
            delta = -1
        self.canvas.yview_scroll(delta, "units")

class Scroll(TkBaseWidget):
    use_ttk = "TFrame"
    END = -0.0
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.align_x = 0
        self.align_y = 0
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.align_x = prev.align_x
            self.align_y = prev.align_y
        else:
            self.ui = ScrollableFrame(self.tkparent.inner)
        self.ui.puinode = self
        self.ui.set_scroll(self.vertical, self.horizontal)

        super().update(prev)

    def preSync(self):
        bbox = self.ui.canvas.bbox("all")
        _, _, w, h = bbox
        hsb = self.ui.scroll_x
        if self.align_x == 0:
            self.hsb_offset = hsb.get()[0] * w
        else:
            self.hsb_offset = w - hsb.get()[1] * w
        vsb = self.ui.scroll_y
        if self.align_y == 0:
            self.vsb_offset = vsb.get()[0] * h
        else:
            self.vsb_offset = h - vsb.get()[1] * h

    def postSync(self):
        self.ui.winfo_toplevel().update_idletasks()

        oldincx = self.ui.canvas["xscrollincrement"]
        oldincy = self.ui.canvas["yscrollincrement"]
        self.ui.canvas["xscrollincrement"] = 1
        self.ui.canvas["yscrollincrement"] = 1

        bbox = self.ui.canvas.bbox("all")
        _, _, w, h = bbox
        if self.align_x == 0:
            self.ui.canvas.xview_moveto(0.0)
            self.ui.canvas.xview_scroll(int(self.hsb_offset), "units")
        else:
            self.ui.canvas.xview_moveto(1.0)
            self.ui.canvas.xview_scroll(int(-self.hsb_offset), "units")
        if self.align_y == 0:
            self.ui.canvas.yview_moveto(0.0)
            self.ui.canvas.yview_scroll(int(self.vsb_offset), "units")
        else:
            self.ui.canvas.yview_moveto(1.0)
            self.ui.canvas.yview_scroll(int(-self.vsb_offset), "units")

        self.ui.canvas["xscrollincrement"] = oldincx
        self.ui.canvas["yscrollincrement"] = oldincy

    def addChild(self, idx, child):
        if idx:
            return
        child_outer = child.outer
        if child_outer:
            child_outer.grid(row=idx, column=0, sticky='nsew')

    def removeChild(self, idx, child):
        child.outer.grid_forget()

    def scrollX(self, pos=0):
        if math.copysign(1, pos) >= 0:
            self.align_x = 0
            self.hsb_offset = pos
        else:
            self.align_x = 1
            self.hsb_offset = abs(pos)
        return self

    def scrollY(self, pos=0):
        if math.copysign(1, pos) >= 0:
            self.align_y = 0
            self.vsb_offset = pos
        else:
            self.align_y = 1
            self.vsb_offset = abs(pos)
        return self