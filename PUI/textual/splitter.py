"""Split panes using Textual's public layout, capture and keyboard APIs."""
from textual.geometry import Region, NULL_OFFSET
from textual.layout import Layout, WidgetPlacement
from textual.widget import Widget
from .base import TBase


class _Layout(Layout):
    name = 'pui-splitter'

    def arrange(self, parent, children, size, greedy=True):
        panes, weights = parent.panes, parent.weights
        total = size.height if parent.vertical else size.width
        usable = max(0, total - len(parent.handles))
        weight = sum(weights) or 1
        edges, accumulated = [0], 0
        for value in weights:
            accumulated += value
            edges.append(round(usable * accumulated / weight))
        placements = []
        for index, pane in enumerate(panes):
            start, length = edges[index] + index, edges[index + 1] - edges[index]
            region = Region(0, start, size.width, length) if parent.vertical else Region(start, 0, length, size.height)
            if pane in children:
                margin = pane.styles.margin
                placements.append(WidgetPlacement(region.shrink(margin), NULL_OFFSET, margin, pane, index * 2))
            if index < len(parent.handles):
                handle = parent.handles[index]
                region = Region(0, start + length, size.width, 1) if parent.vertical else Region(start + length, 0, 1, size.height)
                if handle in children:
                    placements.append(WidgetPlacement(region, NULL_OFFSET, handle.styles.margin, handle, index * 2 + 1))
        return placements


class _Handle(Widget, can_focus=True):
    DEFAULT_CSS = """
    _Handle { background: $panel; color: $text-muted; }
    _Handle:hover, _Handle:focus { background: $accent; color: $text; }
    """

    def __init__(self, owner, index):
        super().__init__()
        self.owner, self.index = owner, index
        self.drag = None
        self.tooltip = 'Drag to resize panes; arrows, Home/End also work'

    def render(self):
        return '─' * self.size.width if self.owner.vertical else '\n'.join('│' for _ in range(self.size.height))

    def coordinate(self, event):
        return event.screen_y if self.owner.vertical else event.screen_x

    def on_mouse_down(self, event):
        if event.button != 1:
            return
        event.stop()
        self.focus()
        self.capture_mouse()
        left, right = self.owner.sizes(self.index)
        self.drag = (self.coordinate(event), left, left + right,
                     sum(self.owner.weights[self.index:self.index + 2]))

    def on_mouse_move(self, event):
        if self.drag is not None:
            event.stop()
            start, left, total, weight = self.drag
            self.owner.resize(self.index, left + self.coordinate(event) - start, total, weight)

    def on_mouse_up(self, event):
        if self.drag is not None:
            event.stop()
            self.drag = None
            self.release_mouse()

    def on_unmount(self):
        self.release_mouse()

    def on_key(self, event):
        negative, positive = ('up', 'down') if self.owner.vertical else ('left', 'right')
        key = event.key.removeprefix('shift+')
        if key not in (negative, positive, 'home', 'end'):
            return
        event.stop()
        event.prevent_default()
        left, right = self.owner.sizes(self.index)
        total = left + right
        desired = 1 if key == 'home' else total - 1 if key == 'end' else (
            left + (-1 if key == negative else 1) * (5 if event.key.startswith('shift+') else 1))
        self.owner.resize(self.index, desired, total, sum(self.owner.weights[self.index:self.index + 2]))


class _Splitter(Widget):
    def __init__(self):
        self.split_layout = _Layout()
        self.signature = None
        self.vertical = False
        self.panes, self.weights, self.handles = [], [], []
        super().__init__()

    @property
    def layout(self):
        return self.split_layout

    def sync(self, panes, vertical):
        signature = (vertical, tuple(panes))
        if signature != self.signature:
            for handle in self.handles:
                handle.remove()
            self.panes, self.vertical = panes, vertical
            self.weights = [1] * len(panes)
            self.handles = [_Handle(self, index) for index in range(len(panes) - 1)]
            if self.handles:
                self.mount(*self.handles)
            self.signature = signature
        self.refresh(layout=True)

    def sizes(self, index):
        return [pane.region.height if self.vertical else pane.region.width for pane in self.panes[index:index + 2]]

    def resize(self, index, size, total, weight):
        if total <= 2:
            return
        fraction = max(1, min(total - 1, size)) / total
        self.weights[index:index + 2] = [weight * fraction, weight * (1 - fraction)]
        # A child layout refresh invalidates Textual's cached parent arrangement.
        self.handles[index].refresh(layout=True)


class Splitter(TBase):
    pui_reflow_children = True
    expand_x_prio = 2
    expand_y_prio = 2

    def __init__(self, vertical: bool = False):
        super().__init__()
        self.vertical = bool(vertical)
        self.container_x, self.container_y = not self.vertical, self.vertical

    def update(self, prev):
        self.ui = prev.ui if prev is not None else _Splitter()
        self.mounted = prev.mounted if prev is not None else []
        super().update(prev)

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)
        self.ui.mount(child.outer)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        child.tremove()

    def postSync(self):
        self.mounted[:] = [child.get_node() for child in self.mounted]
        self.ui.sync([child.outer for child in self.mounted if child._visible], self.vertical)
        super().postSync()
