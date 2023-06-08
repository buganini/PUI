from .. import *
from .base import *
from tkinter.scrolledtext import ScrolledText

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
        # self.winfo_toplevel().update_idletasks()

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
            self.canvas.config(yscrollcommand=self.scroll_y.set)
            self.scroll_y.grid(row=0, column=1, sticky="ns")

            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_y)
            self.canvas.bind("<Button-4>", self._on_mousewheel_y)
            self.canvas.bind("<Button-5>", self._on_mousewheel_y)
        else:
            self.scroll_y.grid_forget()

        self.should_scroll_x = self.horizontal or (self.horizontal is None and w > self.canvas.winfo_width())
        if self.should_scroll_x:
            self.scroll_x.config(command=self.canvas.xview)
            self.canvas.config(xscrollcommand=self.scroll_x.set)
            self.scroll_x.grid(row=1, column=0, sticky="ew")
        else:
            self.scroll_x.grid_forget()

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

class TkScroll(TkBaseWidget):
    use_ttk = "TFrame"
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ScrollableFrame(self.tkparent.inner)
        self.ui.set_scroll(self.vertical, self.horizontal)
        super().update(prev)

    def addChild(self, idx, child):
        if idx:
            return
        child_outer = child.outer
        if child_outer:
            child_outer.grid(row=idx, column=0, sticky='nsew')

    def removeChild(self, idx, child):
        child.outer.grid_forget()
