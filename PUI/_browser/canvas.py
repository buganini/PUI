"""Measured Canvas display lists with one independent presentation credit."""
from dataclasses import dataclass

from ..common import Anchor
from .widgets import BrowserNode, color as paint_color
from .images import ImageResource

POINTER_HANDLERS = {'click': ('_onClicked', '_clicked'), 'dblclick': ('_onDblClicked', '_dblclicked'),
    'mousedown': ('_onMouseDown', '_mousedown'), 'mouseup': ('_onMouseUp', '_mouseup'),
    'mousemove': ('_onMouseMove', '_mousemove'), 'mouseenter': ('_onMouseEnter', '_mouseenter'),
    'mouseleave': ('_onMouseLeave', '_mouseleave'), 'wheel': ('_onWheel', '_wheel')}


def command_color(value):
    # Convert PUI RGB integers; let Canvas 2D interpret other serializable values.
    return '#%06x' % value if type(value) is int else value


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


class Canvas(BrowserNode):
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

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        self._record({'op': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                      'color': command_color(color), 'width': width})

    def drawPolyline(self, coords, color=None, width=1):
        self._record({'op': 'polyline', 'points': points(coords),
                      'color': command_color(color), 'width': width})

    def drawCubicBezier(self, start, control1, control2, end, color=None, width=1):
        self._record({'op': 'cubic', 'start': point(start), 'control1': point(control1),
                      'control2': point(control2), 'end': point(end),
                      'color': command_color(color), 'width': width})

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        self._record({'op': 'polygon', 'points': points(coords),
                      'fill': command_color(fill), 'stroke': command_color(stroke), 'width': width})

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        self._record({'op': 'rect', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                      'fill': command_color(fill), 'stroke': command_color(stroke), 'width': width})

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        self._record({'op': 'ellipse', 'x': x, 'y': y, 'rx': rx, 'ry': ry,
                      'fill': command_color(fill), 'stroke': command_color(stroke), 'width': width})

    def drawText(self, x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP):
        text = str(text)
        if len(text) > 65536:
            raise ValueError('Canvas text exceeds 65536 characters')
        self._record({'op': 'text', 'x': x, 'y': y, 'text': text, 'w': w, 'h': h,
                      'size': size, 'color': command_color(color), 'rotate': rotate,
                      'anchor': anchor.name if isinstance(anchor, Anchor) else anchor})

    def drawShapely(self, shape, fill=None, stroke=None, width=1):
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
            self._record({'op': 'path', 'subpaths': subpaths, 'fill_rule': 'evenodd',
                          'fill': command_color(fill), 'stroke': command_color(stroke), 'width': width})
        elif hasattr(shape, 'x') and hasattr(shape, 'y'):
            self.drawEllipse(shape.x, shape.y, width / 2, width / 2, fill=stroke)
        elif hasattr(shape, 'coords'):
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise TypeError('Unsupported Canvas geometry: ' + type(shape).__name__)

    def loadImage(self, image_path):
        return ImageResource.load(image_path)

    def drawImage(self, image, x=0, y=0, width=None, height=None, src_x=0, src_y=0, src_width=None, src_height=None, opacity=1.0):
        self._record({'op': 'image', 'resource': self.runtime.images.register(image.path),
                      'transforms': [list(op) for op in image.operations], 'x': x, 'y': y,
                      'width': width, 'height': height, 'src_x': src_x, 'src_y': src_y,
                      'src_width': src_width, 'src_height': src_height, 'opacity': opacity})
