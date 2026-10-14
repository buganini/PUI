"""Measured Canvas display lists with one independent presentation credit."""
from dataclasses import dataclass
import math
from numbers import Real

from ..common import Anchor
from .widgets import WebNode, color as paint_color
from .protocol import validate_data


def number(value, minimum=-1e9):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or not minimum <= value <= 1e9:
        raise ValueError('Canvas arguments must be bounded finite numbers')
    return float(value)


def point(value):
    x, y = value
    return [number(x), number(y)]


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


class Canvas(WebNode):
    wire_type = 'Canvas'

    def __init__(self, painter, *args):
        super().__init__()
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
        return {}

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
            validate_data(frame)
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

    def _record(self, op, **fields):
        if self._commands is None:
            raise RuntimeError('Canvas drawing commands require an active painter callback')
        if len(self._commands) >= 10000:
            raise ValueError('Canvas frame exceeds 10000 commands')
        self._commands.append(dict(op=op, **fields))

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        self._record('line', x1=number(x1), y1=number(y1), x2=number(x2), y2=number(y2),
                     color=paint_color(color), width=number(width, 0))

    def drawPolyline(self, coords, color=None, width=1):
        self._record('polyline', points=points(coords),
                     color=paint_color(color), width=number(width, 0))

    def drawCubicBezier(self, start, control1, control2, end, color=None, width=1):
        self._record('cubic', start=point(start), control1=point(control1), control2=point(control2),
                     end=point(end), color=paint_color(color), width=number(width, 0))

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        self._record('polygon', points=points(coords), fill=paint_color(fill), stroke=paint_color(stroke), width=number(width, 0))

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        self._record('rect', x1=number(x1), y1=number(y1), x2=number(x2), y2=number(y2),
                     fill=paint_color(fill), stroke=paint_color(stroke), width=number(width, 0))

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        self._record('ellipse', x=number(x), y=number(y), rx=number(rx, 0), ry=number(ry, 0),
                     fill=paint_color(fill), stroke=paint_color(stroke), width=number(width, 0))

    def drawText(self, x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP):
        if not isinstance(anchor, Anchor):
            raise ValueError('Canvas text anchor must be an Anchor')
        text = str(text)
        if len(text) > 65536:
            raise ValueError('Canvas text exceeds 65536 characters')
        self._record('text', x=number(x), y=number(y), text=str(text),
                     w=None if w is None else number(w, 0), h=None if h is None else number(h, 0),
                     size=None if size is None else number(size, 0), color=paint_color(color),
                     rotate=number(rotate), anchor=anchor.name)

    def drawImage(self, image, x=0, y=0, width=None, height=None, src_x=0, src_y=0, src_width=None, src_height=None, opacity=1.0):
        raise NotImplementedError('Web Canvas image resources are not implemented')
