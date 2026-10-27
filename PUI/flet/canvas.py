from __future__ import annotations
from .. import _typing as _t
from .._canvas import CanvasScope
from .base import *
import math
from functools import partial
import flet.canvas as cv


class Canvas(CanvasScope, FBase):
    expand_x_prio, expand_y_prio = 4, 4
    pui_terminal = True

    def __init__(self, painter: _t.Callback, *args: _t.Any) -> None:
        super().__init__()
        self.painter, self.args = painter, args
        self.pixel_density = 1.0
        self.width = self.height = 0
        self.gesture = None
        self._paint_styles = {}
        self._input_state = {'double_position': None, 'pressed': {}}

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui = prev.ui
            self.width, self.height = prev.width, prev.height
            self.gesture = prev.gesture
            self._input_state = prev._input_state
        else:
            self.ui = cv.Canvas()
            self.gesture = ft.GestureDetector(content=self.ui)
        self.ui.on_resize = self.on_resize
        super().update(prev)
        self._apply_canvas_size()
        # Flet rejects a GestureDetector with no handlers. Keep drawing-only
        # canvases native, including when the last handler is removed.
        self.shell.content = self.gesture if self.update_events() else self.ui
        self.paint(notify=False)

    def _apply_canvas_size(self):
        from ..expansion import physical_children, physical_parent, priority
        parent = physical_parent(self)
        sizes = []
        for axis in ('x', 'y'):
            demand = priority(self, axis, parent)
            grows = demand > 0
            if parent is not None and getattr(parent, 'container_' + axis, False):
                highest = max((priority(child, axis, parent)
                               for child in physical_children(parent)), default=0)
                grows = grows and demand == highest
            # Canvas.expand needs finite natural sizes on non-growing axes:
            # a Row/Column supplies unbounded constraints to compact children.
            sizes.append(None if grows else (self._minimum_size(axis) or 0))
        self.ui.width, self.ui.height = sizes
        self.shell.width, self.shell.height = sizes
        self.shell.alignment = ft.Alignment.TOP_LEFT
        self.ui.expand = self.gesture.expand = any(size is None for size in sizes)
        if sizes[0] is not None:
            self.width = sizes[0]
        if sizes[1] is not None:
            self.height = sizes[1]

    def postSync(self):
        self._apply_canvas_size()
        super().postSync()

    def update_events(self):
        for event, callback in (('hover', '_onMouseMove'), ('enter', '_onMouseEnter'),
                                ('exit', '_onMouseLeave')):
            setattr(self.gesture, 'on_' + event,
                    partial(self.on_pointer, callback=callback) if getattr(self, callback) else None)
        double = bool(self._onDblClicked)
        self.gesture.on_double_tap_down = self.on_double_down if double else None
        self.gesture.on_double_tap = self.on_double if double else None
        self.gesture.on_double_tap_cancel = self.on_double_cancel if double else None
        if not double:
            self._input_state['double_position'] = None
        pointer = any((self._onMouseDown, self._onMouseUp, self._onMouseMove))
        handlers = {
            'pan_down': self.on_down,
            'pan_start': self.on_pan_start,
            'pan_update': self.on_drag,
            'pan_end': self.on_up,
            'tap_up': self.on_up,
            'tap_cancel': partial(self.on_primary_cancel, recognizer='tap'),
            'pan_cancel': partial(self.on_primary_cancel, recognizer='pan'),
            'right_pan_start': partial(self.on_down, button=MouseButton.RIGHT),
            'right_pan_update': partial(self.on_drag, button=MouseButton.RIGHT),
            'right_pan_end': partial(self.on_up, button=MouseButton.RIGHT),
            'tertiary_tap_down': partial(self.on_down, button=MouseButton.MIDDLE),
            'tertiary_tap_up': partial(self.on_up, button=MouseButton.MIDDLE),
            'tertiary_tap_cancel': partial(self.on_cancel, button=MouseButton.MIDDLE),
        }
        for name, handler in handlers.items():
            setattr(self.gesture, 'on_' + name, handler if pointer else None)
        self.gesture.on_scroll = self.on_scroll if self._onWheel else None
        if not pointer:
            self._input_state['pressed'].clear()
        return pointer or double or any((self._onMouseEnter, self._onMouseLeave, self._onWheel))

    def dispatch_pointer(self, position, callback, button=MouseButton.NONE, **fields):
        node = self.get_node()
        if node.destroyed or position is None:
            return
        handler = getattr(node, callback)
        if handler:
            event = PUIEvent()
            event.x, event.y = position.x, position.y
            event.button = button
            event.__dict__.update(fields)
            cb, args, kwargs = handler
            cb(event, *args, **kwargs)

    async def on_pointer(self, event, callback):
        self.dispatch_pointer(event.local_position, callback)

    async def on_down(self, event, button=MouseButton.LEFT):
        node = self.get_node()
        if node.destroyed or not any((node._onMouseDown, node._onMouseUp, node._onMouseMove)):
            return
        # Double-tap recognition can consume a tap's normal up notification.
        # A new press ends any leftover candidate as cancelled, not released.
        await node.on_cancel(event, button)
        node = node.get_node()
        if node.destroyed or not any((node._onMouseDown, node._onMouseUp, node._onMouseMove)):
            return
        node._input_state['pressed'][button] = {
            'position': event.local_position, 'dragging': False, 'cancelled': set()}
        node.dispatch_pointer(event.local_position, '_onMouseDown', button)

    async def on_pan_start(self, event):
        node = self.get_node()
        if node.destroyed:
            return
        press = node._input_state['pressed'].get(MouseButton.LEFT)
        if press is not None:
            press['dragging'] = True
            await node.on_drag(event)

    async def on_drag(self, event, button=MouseButton.LEFT):
        node = self.get_node()
        if node.destroyed:
            return
        press = node._input_state['pressed'].get(button)
        if press is not None:
            press['position'] = event.local_position
            node.dispatch_pointer(event.local_position, '_onMouseMove', button)

    async def on_up(self, event, button=MouseButton.LEFT):
        node = self.get_node()
        if not node.destroyed and node._input_state['pressed'].pop(button, None) is not None:
            node.dispatch_pointer(event.local_position, '_onMouseUp', button, cancelled=False)

    async def on_primary_cancel(self, event, recognizer):
        node = self.get_node()
        if node.destroyed:
            return
        press = node._input_state['pressed'].get(MouseButton.LEFT)
        if press is None:
            return
        press['cancelled'].add(recognizer)
        # A tap loses to a drag, and a pan loses to a tap. Neither by itself
        # ends contact; only cancellation of both ends the primary sequence.
        if not press['dragging'] and press['cancelled'] == {'tap', 'pan'}:
            await node.on_cancel(event, MouseButton.LEFT)

    async def on_cancel(self, event, button):
        node = self.get_node()
        if node.destroyed:
            return
        press = node._input_state['pressed'].pop(button, None)
        if press is not None:
            node.dispatch_pointer(press['position'], '_onMouseUp', button, cancelled=True)

    async def on_scroll(self, event):
        self.dispatch_pointer(event.local_position, '_onWheel',
                              x_delta=-event.scroll_delta.x, y_delta=-event.scroll_delta.y,
                              h_delta=0, v_delta=0, modifiers=None)

    async def on_double_down(self, event):
        node = self.get_node()
        if not node.destroyed and node._onDblClicked:
            node._input_state['double_position'] = event.local_position

    async def on_double(self, event):
        node = self.get_node()
        if not node.destroyed:
            position = node._input_state.pop('double_position', None)
            await node.on_cancel(event, MouseButton.LEFT)
            node.dispatch_pointer(position, '_onDblClicked', MouseButton.LEFT)

    async def on_double_cancel(self, event):
        node = self.get_node()
        if not node.destroyed:
            node._input_state['double_position'] = None

    def releaseRetiredRefs(self):
        self.gesture = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self._input_state.clear()
        if self.gesture is not None:
            for name in ('hover', 'enter', 'exit', 'double_tap_down', 'double_tap', 'double_tap_cancel',
                         'pan_down', 'pan_start', 'pan_update', 'pan_end', 'pan_cancel',
                         'tap_up', 'tap_cancel', 'right_pan_start', 'right_pan_update', 'right_pan_end',
                         'tertiary_tap_down', 'tertiary_tap_up', 'tertiary_tap_cancel', 'scroll'):
                setattr(self.gesture, 'on_' + name, None)
        self.gesture = None
        super().destroy(direct)

    def on_resize(self, event):
        node = self.get_node()
        if not node.destroyed and (node.width, node.height) != (event.width, event.height):
            node.width, node.height = event.width, event.height
            node.paint()

    def paint(self, notify=True):
        node = self.get_node()
        if (node.destroyed or node.ui is None
                or not all(math.isfinite(size) and size > 0 for size in (node.width, node.height))):
            return
        node.ui.shapes.clear()
        node._paint_styles.clear()
        try:
            immediate = node.painter(node, *node.args)
        finally:
            # Shapes retain their Paint values for Flet serialization; the
            # lookup is local to this callback and never mutates those values.
            node._paint_styles.clear()
        app = FView.application(node)
        if app is not None and app.ready:
            if notify:
                app.ui.update()
            if immediate:
                app.loop.call_soon(node.paint, context=app.context.copy())

    def _paint_style(self, color, style, width=0.0):
        key = (color, style, width)
        if key not in self._paint_styles:
            self._paint_styles[key] = ft.Paint(color=colour(color), stroke_width=width, style=style)
        return self._paint_styles[key]

    def drawText(
        self,
        x: _t.Number,
        y: _t.Number,
        text: _t.Any,
        w: _t.Number | None = None,
        h: _t.Number | None = None,
        size: _t.Number = 12,
        color: int | None = None,
        rotate: _t.Number = 0,
        anchor: Anchor = Anchor.LeftTop,
    ) -> None:
        alignment = ft.Alignment({'left': -1, 'center': 0, 'right': 1}[anchor.value[0]],
                                 {'top': -1, 'center': 0, 'bottom': 1}[anchor.value[1]])
        self.ui.shapes.append(cv.Text(x, y, value=text,
                                     style=ft.TextStyle(size=size, color=colour(color)),
                                     alignment=alignment, rotate=math.radians(rotate),
                                     max_width=float('inf') if w is None else w))

    def drawLine(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if color is not None:
            self.ui.shapes.append(cv.Line(x1, y1, x2, y2,
                                         self._paint_style(color, ft.PaintingStyle.STROKE, width)))

    def drawPolyline(self, coords: _t.Points, color: int | None = None, width: _t.Number = 1) -> None:
        coords = list(coords)
        if color is None or len(coords) < 2:
            return
        elements = [cv.Path.MoveTo(*coords[0])] + [cv.Path.LineTo(*point) for point in coords[1:]]
        self.ui.shapes.append(cv.Path(elements=elements,
                                     paint=self._paint_style(color, ft.PaintingStyle.STROKE, width)))

    def drawCubicBezier(
        self,
        start: _t.Point,
        control1: _t.Point,
        control2: _t.Point,
        end: _t.Point,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if color is not None:
            self.ui.shapes.append(cv.Path(elements=[cv.Path.MoveTo(*start),
                                                   cv.Path.CubicTo(*control1, *control2, *end)],
                                         paint=self._paint_style(color, ft.PaintingStyle.STROKE, width)))

    def shape(self, constructor, fill, stroke, width):
        if fill is not None:
            self.ui.shapes.append(constructor(self._paint_style(fill, ft.PaintingStyle.FILL)))
        if stroke is not None:
            self.ui.shapes.append(constructor(self._paint_style(stroke, ft.PaintingStyle.STROKE, width)))

    def drawPolygon(
        self,
        coords: _t.Points,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        coords = list(coords)
        if len(coords) < 3:
            return
        elements = [cv.Path.MoveTo(*coords[0])] + [cv.Path.LineTo(*point) for point in coords[1:]] + [cv.Path.Close()]
        self.shape(lambda paint: cv.Path(elements=elements, paint=paint), fill, stroke, width)

    def drawRect(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self.shape(lambda paint: cv.Rect(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1), paint=paint),
                   fill, stroke, width)

    def drawEllipse(
        self,
        x: _t.Number,
        y: _t.Number,
        rx: _t.Number,
        ry: _t.Number,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self.shape(lambda paint: cv.Oval(x-rx, y-ry, rx*2, ry*2, paint=paint), fill, stroke, width)
