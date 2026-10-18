"""Measured Canvas display lists with one independent presentation credit."""
from __future__ import annotations
from .. import _typing as _t
from .._canvas import CanvasScope
from dataclasses import dataclass
from functools import lru_cache

from ..common import Anchor
from .widgets import BrowserNode, color as paint_color
from .images import ImageResource

POINTER_HANDLERS = {'click': ('_onClicked', '_clicked'), 'dblclick': ('_onDblClicked', '_dblclicked'),
    'mousedown': ('_onMouseDown', '_mousedown'), 'mouseup': ('_onMouseUp', '_mouseup'),
    'mousemove': ('_onMouseMove', '_mousemove'), 'mouseenter': ('_onMouseEnter', '_mouseenter'),
    'mouseleave': ('_onMouseLeave', '_mouseleave'), 'wheel': ('_onWheel', '_wheel')}


@lru_cache(maxsize=128)
def _integer_color(value):
    return '#%06x' % value


def command_color(value):
    # Convert PUI RGB integers; let Canvas 2D interpret other serializable values.
    return _integer_color(value) if type(value) is int else value


def point(value):
    return list(value)


def points(values):
    result = []
    for value in values:
        if len(result) >= 20000:
            raise ValueError('Canvas command exceeds 20000 points')
        result.append(point(value))
    return result


@dataclass
class Drawing:
    measure: object = None
    frame: object = None
    revision: int = 0
    dirty: bool = True
    awaiting: bool = False


class Canvas(CanvasScope, BrowserNode):
    wire_type = 'Canvas'
    pointer_handlers = POINTER_HANDLERS

    def pointer(self, name, data):
        from ..node import PUIEvent
        event = PUIEvent()
        event.__dict__.update(data)
        if name == 'wheel':
            event.x_delta = -data['delta_x'] if data['delta_mode'] == 'pixel' else 0
            event.y_delta = -data['delta_y'] if data['delta_mode'] == 'pixel' else 0
            event.h_delta = event.v_delta = 0
        getattr(self, self.pointer_handlers[name][1])(event)

    def __init__(self, painter: _t.Callback, *args: _t.Any, show_fps: bool = False) -> None:
        super().__init__()
        self.show_fps = show_fps
        self.painter, self.args = painter, args
        self.drawing = Drawing()
        self.width = self.height = 0
        self.pixel_density = 1.0
        self._commands = None

    def update(self, prev):
        if prev is not None:
            self.drawing = prev.drawing
        self.drawing.dirty = True
        super().update(prev)

    def properties(self):
        return {"show_fps": True} if self.show_fps else {}

    def measure(self, body):
        drawing = self.drawing
        if drawing.measure is not None and body['measure_rev'] <= drawing.measure['measure_rev']:
            return False
        drawing.measure = dict(body)
        drawing.frame = None
        drawing.dirty, drawing.awaiting = True, False
        return True

    def reset_connection(self):
        self.drawing.measure = self.drawing.frame = None
        self.drawing.dirty, self.drawing.awaiting = True, False

    def frame(self):
        drawing = self.drawing
        measure = drawing.measure
        if (measure is None or not measure['visible'] or
                measure['width'] <= 0 or measure['height'] <= 0):
            return None
        if drawing.dirty and not drawing.awaiting:
            self.width, self.height, self.pixel_density = measure['width'], measure['height'], measure['dpr']
            # Published frames remain read-only while the render stream retains
            # them. Every paint builds a new command list and frame.
            commands = self._commands = []
            try:
                continuous = bool(self.painter(self, *self.args))
            finally:
                self._commands = None
            drawing.revision += 1
            frame = {'node_id': self.ui.id, 'frame_rev': drawing.revision,
                'measure_rev': measure['measure_rev'], 'width': self.width, 'height': self.height,
                'dpr': self.pixel_density, 'background': paint_color(self.style_bgcolor),
                'continue': continuous, 'commands': commands}
            drawing.frame = frame
            drawing.dirty, drawing.awaiting = False, True
        return drawing.frame

    def acknowledge(self, body):
        drawing = self.drawing
        frame = drawing.frame
        if (frame is None or not drawing.awaiting or body['frame_rev'] != frame['frame_rev'] or
                body['measure_rev'] != frame['measure_rev']):
            return False
        drawing.awaiting = False
        if body['status'] in ('drawn', 'unchanged'):
            drawing.dirty |= frame['continue']
            return drawing.dirty
        # Hidden/stale frames wait for a newer measurement; they cannot sustain
        # a continuous painter loop with no actual presentation.
        return False

    def _record(self, command):
        if self._commands is None:
            raise RuntimeError('Canvas drawing commands require an active painter callback')
        if len(self._commands) >= 300000:
            raise ValueError('Canvas frame exceeds 300000 commands')
        self._commands.append(command)

    def drawLine(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self._record(('line', x1, y1, x2, y2, command_color(color), width))

    def drawPolyline(self, coords: _t.Points, color: int | None = None, width: _t.Number = 1) -> None:
        self._record(('polyline', points(coords), command_color(color), width))

    def drawCubicBezier(
        self,
        start: _t.Point,
        control1: _t.Point,
        control2: _t.Point,
        end: _t.Point,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self._record(('cubic', point(start), point(control1), point(control2),
                      point(end), command_color(color), width))

    def drawPolygon(
        self,
        coords: _t.Points,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self._record(('polygon', points(coords), command_color(fill), command_color(stroke), width))

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
        self._record(('rect', x1, y1, x2, y2, command_color(fill), command_color(stroke), width))

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
        self._record(('ellipse', x, y, rx, ry, command_color(fill), command_color(stroke), width))

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
        anchor: Anchor = Anchor.LEFT_TOP,
    ) -> None:
        text = str(text)
        if len(text) > 65536:
            raise ValueError('Canvas text exceeds 65536 characters')
        self._record(('text', x, y, text, w, h, size, command_color(color), rotate,
                      anchor.name if isinstance(anchor, Anchor) else anchor))

    def drawShapely(
        self,
        shape: _t.Any,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        """Expand existing geometry objects; the Web backend does not import Shapely."""
        if getattr(shape, 'is_empty', False):
            return
        if hasattr(shape, 'geoms'):
            for child in shape.geoms:
                self.drawShapely(child, fill, stroke, width)
        elif hasattr(shape, 'exterior'):
            subpaths = [{'points': points(ring.coords), 'closed': True}
                        for ring in [shape.exterior, *shape.interiors]]
            if sum(len(path['points']) for path in subpaths) > 20000:
                raise ValueError('Canvas path exceeds 20000 points')
            self._record(('path', subpaths, 'evenodd', command_color(fill), command_color(stroke), width))
        elif hasattr(shape, 'x') and hasattr(shape, 'y'):
            self.drawEllipse(shape.x, shape.y, width / 2, width / 2, fill=stroke)
        elif hasattr(shape, 'coords'):
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise TypeError('Unsupported Canvas geometry: ' + type(shape).__name__)

    def loadImage(self, image_path: _t.Any) -> ImageResource:
        return ImageResource.load(image_path)

    def drawImage(
        self,
        image: ImageResource,
        x: _t.Number = 0,
        y: _t.Number = 0,
        width: _t.Number | None = None,
        height: _t.Number | None = None,
        src_x: _t.Number = 0,
        src_y: _t.Number = 0,
        src_width: _t.Number | None = None,
        src_height: _t.Number | None = None,
        opacity: _t.Number = 1.0,
    ) -> None:
        self._record(('image', self.runtime.images.register(image.path),
                      [list(op) for op in image.operations], x, y, width, height,
                      src_x, src_y, src_width, src_height, opacity))
