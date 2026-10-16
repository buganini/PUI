from .base import *
import math
from functools import partial
import flet.canvas as cv


class Canvas(FBase):
    pui_terminal = True

    def __init__(self, painter, *args):
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
        # Canvas.expand fills unspecified axes through Flet's native sizing.
        # Expanding only the outer Container leaves the canvas itself at zero width.
        self.ui.expand = bool(self.layout_weight)
        self.ui.width, self.ui.height = self.layout_width, self.layout_height
        self.width = self.layout_width if self.layout_width is not None else self.width
        self.height = self.layout_height if self.layout_height is not None else self.height
        self.ui.on_resize = self.on_resize
        super().update(prev)
        self.gesture.expand = bool(self.layout_weight)
        # Flet rejects a GestureDetector with no handlers. Keep drawing-only
        # canvases native, including when the last handler is removed.
        self.shell.content = self.gesture if self.update_events() else self.ui
        self.paint(notify=False)

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

    def drawText(self, x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP):
        alignment = ft.Alignment({'left': -1, 'center': 0, 'right': 1}[anchor.value[0]],
                                 {'top': -1, 'center': 0, 'bottom': 1}[anchor.value[1]])
        self.ui.shapes.append(cv.Text(x, y, value=text,
                                     style=ft.TextStyle(size=size, color=colour(color)),
                                     alignment=alignment, rotate=math.radians(rotate),
                                     max_width=float('inf') if w is None else w))

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        if color is not None:
            self.ui.shapes.append(cv.Line(x1, y1, x2, y2,
                                         self._paint_style(color, ft.PaintingStyle.STROKE, width)))

    def drawPolyline(self, coords, color=None, width=1):
        coords = list(coords)
        if color is None or len(coords) < 2:
            return
        elements = [cv.Path.MoveTo(*coords[0])] + [cv.Path.LineTo(*point) for point in coords[1:]]
        self.ui.shapes.append(cv.Path(elements=elements,
                                     paint=self._paint_style(color, ft.PaintingStyle.STROKE, width)))

    def drawCubicBezier(self, start, control1, control2, end, color=None, width=1):
        if color is not None:
            self.ui.shapes.append(cv.Path(elements=[cv.Path.MoveTo(*start),
                                                   cv.Path.CubicTo(*control1, *control2, *end)],
                                         paint=self._paint_style(color, ft.PaintingStyle.STROKE, width)))

    def shape(self, constructor, fill, stroke, width):
        if fill is not None:
            self.ui.shapes.append(constructor(self._paint_style(fill, ft.PaintingStyle.FILL)))
        if stroke is not None:
            self.ui.shapes.append(constructor(self._paint_style(stroke, ft.PaintingStyle.STROKE, width)))

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        coords = list(coords)
        if len(coords) < 3:
            return
        elements = [cv.Path.MoveTo(*coords[0])] + [cv.Path.LineTo(*point) for point in coords[1:]] + [cv.Path.Close()]
        self.shape(lambda paint: cv.Path(elements=elements, paint=paint), fill, stroke, width)

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        self.shape(lambda paint: cv.Rect(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1), paint=paint),
                   fill, stroke, width)

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        self.shape(lambda paint: cv.Oval(x-rx, y-ry, rx*2, ry*2, paint=paint), fill, stroke, width)
