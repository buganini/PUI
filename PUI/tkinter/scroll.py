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

        self.scroll_y = ttk.Scrollbar(self.container, orient=tk.VERTICAL)
        self.scroll_x = ttk.Scrollbar(self.container, orient=tk.HORIZONTAL)
        self.should_scroll_y = False
        self.should_scroll_x = False
        self.last_bbox = None
        self.last_scroll_x = None
        self.last_scroll_y = None

        self.canvas = tk.Canvas(self.container, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        super().__init__(self.canvas)
        self.window_item = self.canvas.create_window(0, 0, window=self, anchor="nw")
        self.columnconfigure(0, weight=1)
        self.canvas.bind("<Configure>", self._on_configure)
        self.bind('<<ThemeChanged>>', self._sync_background, add='+')
        self._sync_background()
        self.wheel_bindings = {}
        top = self.winfo_toplevel()
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.wheel_bindings[sequence] = top.bind(sequence, self._on_mousewheel_y, add='+')

        # Tk 8.7+/9 emits a separate event for precise touchpad gestures.
        if self.tk.call('info', 'commands', 'tk::ScrollByPixels'):
            self.wheel_bindings['<TouchpadScroll>'] = top.bind(
                '<TouchpadScroll>', self._on_touchpad, add='+')

        self.bind("<Configure>", self._on_configure)

    def _sync_background(self, event=None):
        style_name = self.cget('style') or 'TFrame'
        self.container.configure(style=style_name)
        color = ttk.Style(self).lookup(style_name, 'background')
        if color:
            self.canvas.configure(background=color)

    def set_scroll(self, vertical, horizontal):
        self.vertical = vertical
        self.horizontal = horizontal

        self.update_scroller()

    def _on_configure(self, event):
        self.update_scroller()

    def update_scroller(self):
        width = self.canvas.winfo_width() if self.horizontal is False else 0
        if int(self.canvas.itemcget(self.window_item, 'width')) != width:
            self.canvas.itemconfigure(self.window_item, width=width)
        bbox = self.canvas.bbox("all")
        if bbox is None:
            return
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        self.canvas.configure(scrollregion=bbox)
        if self.horizontal is False:
            self.canvas.configure(width=self.winfo_reqwidth())
        if self.vertical is False:
            self.canvas.configure(height=h)

        self.should_scroll_y = self.vertical or (self.vertical is None and h > self.canvas.winfo_height())
        if self.should_scroll_y:
            self.scroll_y.config(command=self.canvas.yview)
            self.canvas.config(yscrollcommand=self._on_scroll_y)
            self.scroll_y.grid(row=0, column=1, sticky="ns")

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

    def _owns_wheel_event(self, event):
        # Toplevel bindings reach descendants; filter to the nearest scroller.
        widget = event.widget
        if widget is self.canvas or widget is self.container:
            widget = self
        while widget is not None and not isinstance(widget, ScrollableFrame):
            if isinstance(widget, tk.Canvas):
                content = next((child for child in widget.winfo_children()
                                if isinstance(child, ScrollableFrame)), None)
                if content is not None:
                    widget = content
                    break
            widget = getattr(widget, 'master', None)
        return widget is self

    def _on_touchpad(self, event):
        if not self._owns_wheel_event(event):
            return
        dx, dy = self.tk.call('tk::PreciseScrollDeltas', event.delta)
        if event.state & 1:  # Shift swaps the gesture axes, as in Tk bindings.
            dx, dy = dy, dx
        dx = dx if self.should_scroll_x else 0
        dy = dy if self.should_scroll_y else 0
        if dx or dy:
            self.tk.call('tk::ScrollByPixels', self.canvas._w, dx, dy)
            return 'break'

    def _on_mousewheel_y(self, event):
        if not self._owns_wheel_event(event) or not self.should_scroll_y:
            return
        if event.num == 5:
            delta = 1
        elif event.num == 4:
            delta = -1
        elif event.delta > 0:
            delta = -1
        elif event.delta < 0:
            delta = 1
        else:
            return
        self.canvas.yview_scroll(delta, 'units')
        return 'break'

    def destroy(self):
        top = self.winfo_toplevel()
        for sequence, binding in self.wheel_bindings.items():
            top.unbind(sequence, binding)
        self.wheel_bindings.clear()
        super().destroy()

class Scroll(TkBaseWidget):
    pui_terminal = False

    ttk_style = "TFrame"
    END = -0.0
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.align_x = 0
        self.align_y = 0
        self.hsb_offset = self.vsb_offset = 0
        self.requests = [None, None]
        self.pending = False
        super().__init__()
        self.expand_x_prio = 1 if horizontal is False else 3
        self.expand_y_prio = 1 if vertical is False else 3

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.align_x = prev.align_x
            self.align_y = prev.align_y
            self.hsb_offset = prev.hsb_offset
            self.vsb_offset = prev.vsb_offset
            self.pending = prev.pending
            for axis in (0, 1):
                request = self.requests[axis]
                if request is not None and request != prev.requests[axis]:
                    alignment, offset = request
                    if axis == 0:
                        self.align_x, self.hsb_offset = alignment, offset
                    else:
                        self.align_y, self.vsb_offset = alignment, offset
                    self.pending = True
                elif request is None:
                    self.requests[axis] = prev.requests[axis]
        else:
            self.ui = ScrollableFrame(self.tkparent.inner)
        self.ui.puinode = self
        self.ui.set_scroll(self.vertical, self.horizontal)

        super().update(prev)
        self.ui._sync_background()

    @property
    def outer(self):
        return self.ui.container if self.ui is not None else None

    def preSync(self):
        if self.pending:
            return
        bbox = self.ui.canvas.bbox("all")
        x0, y0, x1, y1 = bbox or (0, 0, 0, 0)
        w, h = x1 - x0, y1 - y0
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
        if self.destroyed or self.ui is None:
            return
        if self.children:
            child = self.children[0]
            if child._visible:
                self.addChild(0, child)
            else:
                child.outer.grid_remove()
        self.ui.winfo_toplevel().update_idletasks()

        oldincx = self.ui.canvas["xscrollincrement"]
        oldincy = self.ui.canvas["yscrollincrement"]
        self.ui.canvas["xscrollincrement"] = 1
        self.ui.canvas["yscrollincrement"] = 1

        bbox = self.ui.canvas.bbox("all")
        x0, y0, x1, y1 = bbox or (0, 0, 0, 0)
        w, h = x1 - x0, y1 - y0
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
        self.pending = False

    def addChild(self, idx, child):
        if idx:
            return
        child_outer = child.outer
        if child_outer:
            child_outer.grid(row=idx, column=0, sticky='ew' if getattr(child, 'expand_x_prio', 0) else '')

    def removeChild(self, idx, child):
        child.outer.grid_forget()

    def scrollX(self, pos=0):
        self.pending = True
        if math.copysign(1, pos) >= 0:
            self.align_x = 0
            self.hsb_offset = pos
        else:
            self.align_x = 1
            self.hsb_offset = abs(pos)
        self.requests[0] = (self.align_x, self.hsb_offset)
        if self.ui is not None:
            self.ui.after_idle(self.postSync)
        return self

    def scrollY(self, pos=0):
        self.pending = True
        if math.copysign(1, pos) >= 0:
            self.align_y = 0
            self.vsb_offset = pos
        else:
            self.align_y = 1
            self.vsb_offset = abs(pos)
        self.requests[1] = (self.align_y, self.vsb_offset)
        if self.ui is not None:
            self.ui.after_idle(self.postSync)
        return self
