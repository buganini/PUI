from .. import *
from .base import *
from tkinter.scrolledtext import ScrolledText

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, vertical=True, horizontal=False):
        self.container = tk.Frame(parent)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.container)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        super().__init__(self.canvas)
        self.canvas.create_window(0, 0, window=self, anchor="nw")

        self.bind("<Configure>", self._on_configure)

        if vertical:
            self.scroll_y = tk.Scrollbar(self.container, orient=tk.VERTICAL)
            self.scroll_y.config(command=self.canvas.yview)
            self.canvas.config(yscrollcommand=self.scroll_y.set)
            self.scroll_y.grid(row=0, column=1, sticky="ns")

            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_y)
            self.canvas.bind("<Button-4>", self._on_mousewheel_y)
            self.canvas.bind("<Button-5>", self._on_mousewheel_y)

        if horizontal:
            self.scroll_x = tk.Scrollbar(self.container, orient=tk.HORIZONTAL)
            self.scroll_x.config(command=self.canvas.xview)
            self.canvas.config(xscrollcommand=self.scroll_x.set)
            self.scroll_x.grid(row=1, column=0, sticky="ew")

    def grid(self, *args, **kwargs):
        self.container.grid(*args, **kwargs)

    def _on_configure(self, event):
        self.update_layout()

    def update_layout(self):
        bbox = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=bbox)
        self.canvas.configure(width=bbox[2])

    def _on_mousewheel_y(self, event):
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

    def addChild(self, idx, child):
        if idx:
            return
        child.outer.grid(row=idx, column=0, sticky='nsew')

    def postUpdate(self):
        # if not self.layout_weight:
        #     parent = self
        #     while True:
        #         nparent = parent.tkparent
        #         if nparent:
        #             parent = nparent
        #         else:
        #             break

        #     parent.ui.update_idletasks()
            # self.canvas.config(width=self.frame.winfo_reqwidth(), height=self.frame.winfo_reqheight())
        super().postUpdate()

    def removeChild(self, idx, child):
        child.outer.grid_forget()
