"""Resizable panes composed with public Flet controls and drag events."""
from .base import FBase, ft


class _Panes:
    def __init__(self):
        self.signature = None
        self.frames = {}
        self.sizes = {}
        self.handles = []
        self.drag = None

    def set_direction(self, vertical):
        if not hasattr(self, 'row') or self.vertical != vertical:
            self.vertical = vertical
            self.row = (ft.Column(horizontal_alignment=ft.CrossAxisAlignment.STRETCH) if vertical else
                        ft.Row(vertical_alignment=ft.CrossAxisAlignment.STRETCH))
            self.row.spacing = 0
        return self.row

    def sync(self, nodes, vertical):
        widgets = [node.outer for node in nodes if node._visible]
        for widget in list(self.frames):
            if widget not in widgets:
                del self.frames[widget]
                self.sizes.pop(widget, None)
        for widget in widgets:
            if widget not in self.frames:
                async def measure(event, widget=widget):
                    self.sizes[widget] = (event.width, event.height)
                self.frames[widget] = ft.Container(content=widget, expand=1,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE, on_size_change=measure)
        signature = (vertical, tuple(id(widget) for widget in widgets))
        if signature != self.signature:
            self.signature, self.vertical, self.widgets = signature, vertical, widgets
            self.drag = None
            self.handles = [self.handle(index) for index in range(len(widgets) - 1)]
            controls = []
            for index, widget in enumerate(widgets):
                frame = self.frames[widget]
                frame.expand = 10000
                controls.append(frame)
                if index < len(self.handles):
                    controls.append(self.handles[index])
            self.row.controls = controls
        return self.row

    def coordinate(self, event):
        return event.global_position.y if self.vertical else event.global_position.x

    def handle(self, index):
        async def start(event):
            first, second = self.widgets[index:index + 2]
            axis = 1 if self.vertical else 0
            left = self.sizes.get(first, (0, 0))[axis]
            right = self.sizes.get(second, (0, 0))[axis]
            self.drag = (index, self.coordinate(event), left, left + right,
                         self.frames[first].expand + self.frames[second].expand)

        async def update(event):
            if self.drag is None or self.drag[0] != index:
                return
            _, start, left, total, weight = self.drag
            if total <= 2:
                return
            desired = max(1, min(total - 1, left + self.coordinate(event) - start))
            first, second = (self.frames[widget] for widget in self.widgets[index:index + 2])
            first.expand = max(1, min(weight - 1, round(weight * desired / total)))
            second.expand = weight - first.expand
            self.row.update()

        async def end(event):
            self.drag = None

        options = ({'on_vertical_drag_start': start, 'on_vertical_drag_update': update,
                    'on_vertical_drag_end': end, 'on_vertical_drag_cancel': end} if self.vertical else
                   {'on_horizontal_drag_start': start, 'on_horizontal_drag_update': update,
                    'on_horizontal_drag_end': end, 'on_horizontal_drag_cancel': end})
        return ft.GestureDetector(
            content=ft.Container(bgcolor=ft.Colors.OUTLINE_VARIANT,
                                 height=6 if self.vertical else None,
                                 width=None if self.vertical else 6),
            mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN if self.vertical else ft.MouseCursor.RESIZE_LEFT_RIGHT,
            **options)


class Splitter(FBase):
    pui_reflow_children = True
    def __init__(self, vertical: bool = False):
        super().__init__()
        self.vertical = bool(vertical)
        self.container_x, self.container_y = not self.vertical, self.vertical

    def update(self, prev):
        self.panes = prev.panes if prev is not None else _Panes()
        self.mounted = prev.mounted if prev is not None else []
        self.ui = self.panes.set_direction(self.vertical)
        super().update(prev)

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)

    def postSync(self):
        self.mounted[:] = [child.get_node() for child in self.mounted]
        self.ui = self.panes.sync(self.mounted, self.vertical)
        self.shell.content = self.ui
        super().postSync()
