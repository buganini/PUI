"""Themed native split panes with stable child widget parents."""
from .base import TkBaseWidget, ttk


class _Host(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.paned = None
        self.frames = {}
        self.signature = None
        self.reset_id = None

    def sync(self, nodes, vertical):
        # Pane frames and child widgets are siblings under this stable host.
        # Tk's public `in_` geometry option lets a frame lay out that child.
        # Rebuilding the orientation-specific Panedwindow never destroys panes.
        widgets = {node.outer for node in nodes}
        for widget, frame in list(self.frames.items()):
            if widget not in widgets:
                if self.paned is not None and str(frame) in self.paned.panes():
                    self.paned.forget(frame)
                frame.destroy()
                del self.frames[widget]
        for node in nodes:
            widget = node.outer
            if widget not in self.frames:
                frame = self.frames[widget] = ttk.Frame(self)
                frame.columnconfigure(0, weight=1)
                frame.rowconfigure(0, weight=1)
            top, right, bottom, left = node.layout_padding or (0, 0, 0, 0)
            widget.grid(in_=self.frames[widget], row=0, column=0, sticky='nsew',
                        padx=(left, right), pady=(top, bottom))
            widget.lift(self.frames[widget])
        signature = (vertical, tuple(node.outer for node in nodes if node._visible))
        if signature == self.signature:
            return
        if self.reset_id is not None:
            self.after_cancel(self.reset_id)
            self.reset_id = None
        if self.paned is not None:
            for frame in self.paned.panes():
                self.paned.forget(frame)
        if self.paned is None or vertical != self.signature[0]:
            if self.paned is not None:
                self.paned.destroy()
            self.paned = ttk.Panedwindow(self, orient='vertical' if vertical else 'horizontal')
            self.paned.pack(fill='both', expand=True)
            self.paned.lower()
            self.paned.bind('<Configure>', self._on_geometry)
        for widget in signature[1]:
            self.paned.add(self.frames[widget], weight=1)
        self.signature = signature
        self.reset_pending = True
        self._on_geometry()

    def _on_geometry(self, event=None):
        if self.reset_pending and self.reset_id is None:
            self.reset_id = self.after_idle(self._equalize)

    def _equalize(self):
        self.reset_id = None
        vertical, panes = self.signature
        length = self.paned.winfo_height() if vertical else self.paned.winfo_width()
        if length <= 1:
            return
        self.reset_pending = False
        for index in range(len(panes) - 1):
            self.paned.sashpos(index, round(length * (index + 1) / len(panes)))

    def destroy(self):
        if self.reset_id is not None:
            self.after_cancel(self.reset_id)
        super().destroy()


class Splitter(TkBaseWidget):
    pui_terminal = False
    pui_reflow_children = True
    expand_x_prio = 2
    expand_y_prio = 2
    ttk_style = 'TFrame'

    def __init__(self, vertical: bool = False):
        super().__init__()
        self.vertical = bool(vertical)

    def update(self, prev):
        self.ui = prev.ui if prev is not None else _Host(self.tkparent.inner)
        self.mounted = prev.mounted if prev is not None else []
        super().update(prev)

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        child.outer.grid_forget()

    def postSync(self):
        self.mounted[:] = [child.get_node() for child in self.mounted]
        self.ui.sync(self.mounted, self.vertical)
        super().postSync()
