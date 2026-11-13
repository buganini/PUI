"""Immediate-mode Canvas drawn with LVGL's draw API onto an lv_canvas buffer.

Ported from CPPUI's LVGL canvas: polygons and paths are scan-converted into
one-pixel-high rectangles (nonzero/even-odd), curves and ellipses are
flattened, and text is drawn as rotated label images. Path clipping is not
supported (supports_path_clip = False); rectangle clipping is.
"""
from __future__ import annotations
import math
import weakref
from .. import _typing as _t
from .._canvas import CanvasScope, FrameRate
from .._path import path_commands, fill_rule, FillRule
from .._rgba import RGBAImage
from ..common import Anchor
from .base import *
from .font import font_for_size


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _flatten(points, a, b, c, d, depth=0):
    """Append a cubic Bezier as a polyline within a quarter pixel."""
    ux, uy = 3 * b[0] - 2 * a[0] - d[0], 3 * b[1] - 2 * a[1] - d[1]
    vx, vy = 3 * c[0] - 2 * d[0] - a[0], 3 * c[1] - 2 * d[1] - a[1]
    if depth == 12 or max(ux * ux, vx * vx) + max(uy * uy, vy * vy) <= 1:
        points.append(d)
        return
    ab = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    bc = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2)
    cd = ((c[0] + d[0]) / 2, (c[1] + d[1]) / 2)
    abc = ((ab[0] + bc[0]) / 2, (ab[1] + bc[1]) / 2)
    bcd = ((bc[0] + cd[0]) / 2, (bc[1] + cd[1]) / 2)
    mid = ((abc[0] + bcd[0]) / 2, (abc[1] + bcd[1]) / 2)
    _flatten(points, a, ab, abc, mid, depth + 1)
    _flatten(points, mid, bcd, cd, d, depth + 1)


def _contours(commands):
    contours, current, start = [], (0.0, 0.0), (0.0, 0.0)
    for op, *v in commands:
        if op == 'M':
            current = start = (v[0], v[1])
            contours.append([current])
        elif op == 'L':
            current = (v[0], v[1])
            contours[-1].append(current)
        elif op == 'Q':
            end = (v[2], v[3])
            a = (current[0] + 2 * (v[0] - current[0]) / 3, current[1] + 2 * (v[1] - current[1]) / 3)
            b = (end[0] + 2 * (v[0] - end[0]) / 3, end[1] + 2 * (v[1] - end[1]) / 3)
            _flatten(contours[-1], current, a, b, end)
            current = end
        elif op == 'C':
            end = (v[4], v[5])
            _flatten(contours[-1], current, (v[0], v[1]), (v[2], v[3]), end)
            current = end
        else:  # Z
            contours[-1].append(start)
            current = start
    return contours


class ImageResource:
    """A decoded image (file via LVGL decoders, or RGBA bytes) for drawImage."""

    def __init__(self, src, width, height, keep=None):
        self.src = src
        self.width = width
        self.height = height
        self._keep = keep

    @staticmethod
    def load(path):
        path_bytes = ('A:' + str(path)).encode()
        probe = lib.lv_image_create(lib.lv_screen_active())
        try:
            lib.lv_obj_add_flag(probe, lib.LV_OBJ_FLAG_HIDDEN)
            lib.lv_image_set_src(probe, path_bytes)
            width, height = lib.lv_image_get_src_width(probe), lib.lv_image_get_src_height(probe)
        finally:
            lib.lv_obj_delete(probe)
        if width <= 0 or height <= 0:
            raise ValueError(f'Cannot decode image: {path}')
        src = ffi.new('char[]', path_bytes)
        return ImageResource(src, width, height, src)

    @staticmethod
    def from_rgba(image):
        buf = lib.lv_draw_buf_create(image.width, image.height, lib.LV_COLOR_FORMAT_ARGB8888, lib.LV_STRIDE_AUTO)
        if buf == ffi.NULL:
            raise MemoryError('lv_draw_buf_create failed')
        stride = buf.data_size // image.height
        bgra = bytearray(image.data)
        bgra[0::4], bgra[2::4] = bgra[2::4], bgra[0::4]
        row = image.width * 4
        target = ffi.buffer(buf.data, buf.data_size)
        if stride == row:
            target[0:len(bgra)] = bgra
        else:
            for y in range(image.height):
                target[y * stride:y * stride + row] = bgra[y * row:(y + 1) * row]
        resource = ImageResource(buf, image.width, image.height)
        weakref.finalize(resource, lib.lv_draw_buf_destroy, buf)
        return resource


class Canvas(CanvasScope, LBaseWidget):
    expand_x_prio = 4
    expand_y_prio = 4
    supports_path_clip = False
    _default_size = (100, 100)
    _lv_events = (lib.LV_EVENT_SIZE_CHANGED, lib.LV_EVENT_PRESSED, lib.LV_EVENT_RELEASED,
                  lib.LV_EVENT_ROTARY)

    def __init__(self, painter: _t.Callback, *args: _t.Any, show_fps: bool = False) -> None:
        super().__init__()
        self.painter = painter
        self.args = args
        self.show_fps = show_fps
        self.pixel_density = 1.0
        self.width = self.height = 0
        self._layer = None

    # ---- lifecycle ----
    def create(self, parent):
        obj = lib.lv_canvas_create(parent)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
        return obj

    def configure(self, prev):
        store = self._native.store
        if 'on_delete' not in store:
            def released(store=store):
                buf = store.pop('buffer', None)
                if buf is not None:
                    lib.lv_draw_buf_destroy(buf)
                for stale in store.pop('text_buffers', []):
                    lib.lv_draw_buf_destroy(stale)
                _hover.pop(id(store), None)
            store['on_delete'] = [released]
        if self._onMouseMove or self._onMouseLeave or self._onMouseEnter:
            _hover.setdefault(id(store), {'native': self._native, 'inside': False, 'point': None})
            _ensure_poller()
        else:
            _hover.pop(id(store), None)
        self._request_paint()

    def _apply_styles(self):
        super()._apply_styles()
        if (self._onMouseDown or self._onMouseUp or self._onWheel or self._onMouseMove
                or self._onClicked or self._onDblClicked):
            lib.lv_obj_add_flag(self.ui, lib.LV_OBJ_FLAG_CLICKABLE)

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_SIZE_CHANGED:
            self._request_paint()
        elif code in (lib.LV_EVENT_PRESSED, lib.LV_EVENT_RELEASED):
            event = self._pointer_event()
            if event is not None:
                (self._mousedown if code == lib.LV_EVENT_PRESSED else self._mouseup)(event)
            return
        elif code == lib.LV_EVENT_ROTARY:
            diff = ffi.cast('int32_t *', lib.lv_event_get_param(e))[0]
            event = self._pointer_event() or PUIEvent()
            event.v_delta = -120 * diff
            event.h_delta = 0
            event.y_delta = event.x_delta = 0
            event.modifiers = 0
            self._wheel(event)
            return
        super()._lv_event(code, e)

    def _pointer_event(self):
        if self.ui is None:
            return None
        indev = lib.lv_indev_active()
        if indev == ffi.NULL or lib.lv_indev_get_type(indev) != lib.LV_INDEV_TYPE_POINTER:
            # Wheel encoders (X11) and synthetic events: use the mouse position.
            indev = lib.lv_indev_get_next(ffi.NULL)
            while indev != ffi.NULL and lib.lv_indev_get_type(indev) != lib.LV_INDEV_TYPE_POINTER:
                indev = lib.lv_indev_get_next(indev)
            if indev == ffi.NULL:
                return None
        point = ffi.new('lv_point_t *')
        lib.lv_indev_get_point(indev, point)
        area = ffi.new('lv_area_t *')
        lib.lv_obj_get_coords(self.ui, area)
        e = PUIEvent()
        e.x, e.y = point.x - area.x1, point.y - area.y1
        e.button = 1
        return e

    # ---- painting ----
    def _request_paint(self):
        store = self._native.store
        if store.get('paint_pending'):
            return
        store['paint_pending'] = True

        def paint():
            store['paint_pending'] = False
            node = self.get_node()
            if not node.destroyed and node.ui is not None:
                node._paint()
        runtime.post(paint)

    def _paint(self):
        obj = self.ui
        store = self._native.store
        lib.lv_obj_update_layout(obj)
        width, height = lib.lv_obj_get_content_width(obj), lib.lv_obj_get_content_height(obj)
        if width <= 0 or height <= 0:
            return
        buf = store.get('buffer')
        if buf is None or store.get('size') != (width, height):
            new = lib.lv_draw_buf_create(width, height, lib.LV_COLOR_FORMAT_ARGB8888, lib.LV_STRIDE_AUTO)
            if new == ffi.NULL:
                return
            lib.lv_canvas_set_draw_buf(obj, new)
            if buf is not None:
                lib.lv_draw_buf_destroy(buf)
            store['buffer'], store['size'] = new, (width, height)
        # Text images must outlive the draw tasks that referenced them; the
        # previous frame is fully rendered, so release its images now.
        for stale in store.pop('text_buffers', []):
            lib.lv_draw_buf_destroy(stale)
        lib.lv_canvas_fill_bg(obj, lib.lv_color_hex(0), lib.LV_OPA_TRANSP)
        self.width, self.height = width, height
        layer = ffi.new('lv_layer_t *')
        lib.lv_canvas_init_layer(obj, layer)
        self._layer = layer
        self._keep = []
        self._clips = []
        again = False
        try:
            again = self.painter(self, *self.args)
        finally:
            lib.lv_canvas_finish_layer(obj, layer)
            self._layer = None
            self._keep = None
        self._show_fps()
        if again:
            self._request_paint()

    def _show_fps(self):
        store = self._native.store
        label = store.get('fps_label')
        if not self.show_fps:
            if label is not None:
                lib.lv_obj_delete(label)
                store['fps_label'] = None
            return
        if label is None:
            label = store['fps_label'] = lib.lv_label_create(self.ui)
            lib.lv_obj_set_style_bg_color(label, lib.lv_color_hex(0x101A2B), SEL)
            lib.lv_obj_set_style_bg_opa(label, lib.LV_OPA_COVER, SEL)
            lib.lv_obj_set_style_text_color(label, lib.lv_color_hex(0xFFFFFF), SEL)
            lib.lv_obj_set_style_pad_all(label, 4, SEL)
            store['fps'] = FrameRate()
        text = store['fps'].tick()
        if text is not None:
            lib.lv_label_set_text(label, text.encode())
        lib.lv_obj_update_layout(label)
        lib.lv_obj_set_pos(label, max(0, self.width - lib.lv_obj_get_width(label) - 8), 8)

    def _require_layer(self):
        if self._layer is None:
            raise RuntimeError('Canvas drawing methods are only valid inside the painter')
        return self._layer

    # ---- state ----
    def push(self) -> None:
        layer = self._require_layer()
        a = layer._clip_area
        self._clips.append((a.x1, a.y1, a.x2, a.y2))

    def pop(self) -> None:
        layer = self._require_layer()
        if not self._clips:
            raise RuntimeError('Canvas.pop() has no matching push()')
        a = layer._clip_area
        a.x1, a.y1, a.x2, a.y2 = self._clips.pop()

    def clipRect(self, x, y, width, height):
        a = self._require_layer()._clip_area
        bound = lambda v: int(max(-1e9, min(1e9, v)))
        a.x1 = max(a.x1, bound(math.ceil(x)))
        a.y1 = max(a.y1, bound(math.ceil(y)))
        a.x2 = min(a.x2, bound(math.ceil(x + max(0, width))) - 1)
        a.y2 = min(a.y2, bound(math.ceil(y + max(0, height))) - 1)

    # ---- primitives ----
    def _line(self, a, b, color, opa, width):
        dsc = ffi.new('lv_draw_line_dsc_t *')
        lib.lv_draw_line_dsc_init(dsc)
        dsc.color = color
        dsc.opa = opa
        dsc.width = max(1, round(width))
        dsc.p1.x, dsc.p1.y = round(a[0]), round(a[1])
        dsc.p2.x, dsc.p2.y = round(b[0]), round(b[1])
        lib.lv_draw_line(self._layer, dsc)

    def _span_rect(self, color, opa, x1, y1, x2, y2):
        dsc = ffi.new('lv_draw_rect_dsc_t *')
        lib.lv_draw_rect_dsc_init(dsc)
        dsc.bg_color = color
        dsc.bg_opa = opa
        dsc.radius = 0
        area = ffi.new('lv_area_t *', (x1, y1, x2, y2))
        lib.lv_draw_rect(self._layer, dsc, area)

    def _fill_contours(self, contours, fill, rule):
        """Scan-convert closed contours at pixel centers (nonzero or even-odd)."""
        color, opa = lv_color(fill)
        clip = self._layer._clip_area
        ys = [p[1] for points in contours for p in points]
        if not ys:
            return
        top = max(clip.y1, 0, math.floor(min(ys)))
        bottom = min(clip.y2, self.height - 1, math.ceil(max(ys)))
        edges = []
        for points in contours:
            n = len(points)
            for i in range(n):
                a, b = points[i - 1], points[i]
                if a[1] != b[1]:
                    edges.append((a, b))
        even_odd = rule == 'evenodd'
        x_limit = self.width - 1
        for y in range(top, bottom + 1):
            scan = y + 0.5
            crossings = []
            for a, b in edges:
                if (a[1] <= scan < b[1]) or (b[1] <= scan < a[1]):
                    crossings.append((a[0] + (scan - a[1]) * (b[0] - a[0]) / (b[1] - a[1]),
                                      1 if b[1] > a[1] else -1))
            if not crossings:
                continue
            crossings.sort()
            winding = 0
            left = 0.0
            for x, direction in crossings:
                before = (winding % 2 != 0) if even_odd else winding != 0
                winding += direction
                after = (winding % 2 != 0) if even_odd else winding != 0
                if not before and after:
                    left = x
                elif before and not after:
                    x1 = max(0, min(self.width, math.ceil(left - 0.5)))
                    x2 = max(-1, min(x_limit, math.ceil(x - 0.5) - 1))
                    if x1 <= x2:
                        self._span_rect(color, opa, x1, y, x2, y)

    def _stroke_contours(self, contours, stroke, width, close=False):
        color, opa = lv_color(stroke)
        for points in contours:
            for i in range(1, len(points)):
                self._line(points[i - 1], points[i], color, opa, width)
            if close and len(points) > 2:
                self._line(points[-1], points[0], color, opa, width)

    # ---- public drawing API ----
    def drawLine(self, x1: _t.Number, y1: _t.Number, x2: _t.Number, y2: _t.Number,
                 color: int | None = None, width: _t.Number = 1) -> None:
        self._require_layer()
        if color is None:
            return
        c, opa = lv_color(color)
        self._line((x1, y1), (x2, y2), c, opa, width)

    def drawPolyline(self, coords: _t.Points, color: int | None = None, width: _t.Number = 1) -> None:
        self._require_layer()
        coords = [tuple(p) for p in coords]
        if color is None or len(coords) < 2:
            return
        self._stroke_contours([coords], color, width)

    def drawCubicBezier(self, start: _t.Point, control1: _t.Point, control2: _t.Point, end: _t.Point,
                        color: int | None = None, width: _t.Number = 1) -> None:
        self._require_layer()
        if color is None:
            return
        points = [tuple(start)]
        _flatten(points, tuple(start), tuple(control1), tuple(control2), tuple(end))
        self._stroke_contours([points], color, width)

    def drawPolygon(self, coords: _t.Points, fill: int | None = None, stroke: int | None = None,
                    width: _t.Number = 1) -> None:
        self._require_layer()
        points = [tuple(p) for p in coords]
        if not points:
            return
        if fill is not None and len(points) >= 3:
            self._fill_contours([points], fill, 'evenodd')
        if stroke is not None and len(points) > 1:
            self._stroke_contours([points], stroke, width, close=True)

    def drawRect(self, x1: _t.Number, y1: _t.Number, x2: _t.Number, y2: _t.Number,
                 fill: int | None = None, stroke: int | None = None, width: _t.Number = 1) -> None:
        self._require_layer()
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        if fill is not None:
            # Pixel-center coverage, as one native rectangle.
            left = int(min(self.width, max(0, math.ceil(x1 - .5))))
            top = int(min(self.height, max(0, math.ceil(y1 - .5))))
            right = int(max(-1, min(self.width - 1, math.ceil(x2 - .5) - 1)))
            bottom = int(max(-1, min(self.height - 1, math.ceil(y2 - .5) - 1)))
            if left <= right and top <= bottom:
                color, opa = lv_color(fill)
                self._span_rect(color, opa, left, top, right, bottom)
        if stroke is not None:
            self._stroke_contours([[(x1, y2), (x1, y1), (x2, y1), (x2, y2), (x1, y2)]], stroke, width)

    def drawEllipse(self, x: _t.Number, y: _t.Number, rx: _t.Number, ry: _t.Number,
                    fill: int | None = None, stroke: int | None = None, width: _t.Number = 1) -> None:
        self._require_layer()
        if rx <= 0 or ry <= 0:
            return
        count = int(min(4096, max(16, math.ceil(math.pi * math.sqrt(2 * max(rx, ry))))))
        points = [(x + rx * math.cos(2 * math.pi * i / count), y + ry * math.sin(2 * math.pi * i / count))
                  for i in range(count)]
        self.drawPolygon(points, fill, stroke, width)

    def drawPath(self, path, fill=None, stroke=None, width=1, fillRule=FillRule.NonZero):
        self._require_layer()
        commands = path_commands(path)
        rule = fill_rule(fillRule)
        contours = _contours(commands)
        if fill is not None:
            self._fill_contours(contours, fill, rule)
        if stroke is not None:
            self._stroke_contours(contours, stroke, width)

    def drawShapely(self, shape: _t.Any, fill: int | None = None, stroke: int | None = None,
                    width: _t.Number = 1) -> None:
        self._require_layer()
        if hasattr(shape, 'geoms'):
            for geometry in shape.geoms:
                self.drawShapely(geometry, fill, stroke, width)
        elif hasattr(shape, 'exterior'):
            rings = [list(shape.exterior.coords)] + [list(h.coords) for h in shape.interiors]
            if fill is not None:
                self._fill_contours(rings, fill, 'evenodd')
            if stroke is not None:
                self._stroke_contours(rings, stroke, width)
        elif hasattr(shape, 'x') and hasattr(shape, 'y'):
            self.drawEllipse(shape.x, shape.y, width / 2, width / 2, fill=stroke)
        elif hasattr(shape, 'coords'):
            self.drawPolyline(list(shape.coords), color=stroke, width=width)
        else:
            raise RuntimeError(f'Not implemented: drawShapely({type(shape).__name__})')

    def drawText(self, x: _t.Number, y: _t.Number, text: _t.Any, w: _t.Number | None = None,
                 h: _t.Number | None = None, size: _t.Number = 12, color: int | None = None,
                 rotate: _t.Number = 0, anchor: Anchor = Anchor.LeftTop) -> None:
        self._require_layer()
        text = str(text)
        if not text or (size is not None and size <= 0) or any(v is not None and v <= 0 for v in (w, h)):
            return
        font = font_for_size(size) if size is not None else lib.lv_obj_get_style_text_font(self.ui, SEL)
        raw = ffi.new('char[]', text.encode('utf-8'))
        bounds = ffi.new('lv_point_t *')
        lib.lv_text_get_size(bounds, raw, font, 0, 0, lib.LV_COORD_MAX, 0)
        bw = bounds.x + 2 if w is None else min(bounds.x + 2, math.ceil(w))
        bh = bounds.y if h is None else min(bounds.y, math.ceil(h))
        if bw <= 0 or bh <= 0:
            return
        # Without a color, text follows the widget's text color (default black).
        c, opa = lv_color(color if color is not None else
                          self.style_color if self.style_color is not None else 0)
        # Render the text block once, then place it as a rotated image so the
        # anchor and rotation match the other backends (rotate around (x, y)).
        buf = lib.lv_draw_buf_create(bw, bh, lib.LV_COLOR_FORMAT_ARGB8888, lib.LV_STRIDE_AUTO)
        if buf == ffi.NULL:
            return
        lib.lv_draw_buf_clear(buf, ffi.NULL)
        scratch = self._scratch()
        lib.lv_canvas_set_draw_buf(scratch, buf)
        label_layer = ffi.new('lv_layer_t *')
        lib.lv_canvas_init_layer(scratch, label_layer)
        dsc = ffi.new('lv_draw_label_dsc_t *')
        lib.lv_draw_label_dsc_init(dsc)
        dsc.font = font
        dsc.text = raw
        dsc.color = c
        dsc.opa = opa
        area = ffi.new('lv_area_t *', (0, 0, bw - 1, bh - 1))
        lib.lv_draw_label(label_layer, dsc, area)
        lib.lv_canvas_finish_layer(scratch, label_layer)
        self._keep.append((raw, buf))
        self._native.store.setdefault('text_buffers', []).append(buf)

        ax = {'left': 0, 'center': .5, 'right': 1}[anchor.value[0]]
        ay = {'top': 0, 'center': .5, 'bottom': 1}[anchor.value[1]]
        dx, dy = bounds.x * ax, bounds.y * ay
        radians = math.radians(rotate)
        left = round(x - math.cos(radians) * dx + math.sin(radians) * dy)
        top = round(y - math.sin(radians) * dx - math.cos(radians) * dy)
        image = ffi.new('lv_draw_image_dsc_t *')
        lib.lv_draw_image_dsc_init(image)
        image.src = buf
        rotation = int(math.fmod(rotate, 360.0) * 10)
        image.rotation = rotation + 3600 if rotation < 0 else rotation
        image.pivot.x = image.pivot.y = 0
        lib.lv_draw_image(self._layer, image, ffi.new('lv_area_t *', (left, top, left + bw - 1, top + bh - 1)))

    def _scratch(self):
        store = self._native.store
        scratch = store.get('scratch')
        if scratch is None:
            scratch = store['scratch'] = lib.lv_canvas_create(self.ui)
            lib.lv_obj_add_flag(scratch, lib.LV_OBJ_FLAG_HIDDEN)
            lib.lv_obj_add_flag(scratch, lib.LV_OBJ_FLAG_IGNORE_LAYOUT)
        return scratch

    def loadImage(self, image_path: _t.Any) -> ImageResource:
        return ImageResource.load(image_path)

    def drawImage(self, image, x: _t.Number = 0, y: _t.Number = 0, width: _t.Number | None = None,
                  height: _t.Number | None = None, src_x: _t.Number = 0, src_y: _t.Number = 0,
                  src_width: _t.Number | None = None, src_height: _t.Number | None = None,
                  opacity: _t.Number = 1.0) -> None:
        layer = self._require_layer()
        if isinstance(image, RGBAImage):
            image = ImageResource.from_rgba(image)
        self._keep.append(image)
        sw = image.width - src_x if src_width is None else src_width
        sh = image.height - src_y if src_height is None else src_height
        if sw <= 0 or sh <= 0:
            return
        width = sw if width is None else width
        height = sh if height is None else height
        if width <= 0 or height <= 0:
            return
        sx, sy = width / sw, height / sh
        dsc = ffi.new('lv_draw_image_dsc_t *')
        lib.lv_draw_image_dsc_init(dsc)
        dsc.src = image.src
        dsc.scale_x = max(1, round(lib.LV_SCALE_NONE * sx))
        dsc.scale_y = max(1, round(lib.LV_SCALE_NONE * sy))
        dsc.pivot.x = dsc.pivot.y = 0
        dsc.opa = max(0, min(255, round(255 * opacity)))
        left = round(x - src_x * sx)
        top = round(y - src_y * sy)
        # Show only the requested source rectangle at its destination.
        self.push()
        try:
            self.clipRect(x, y, width, height)
            area = ffi.new('lv_area_t *', (left, top, left + image.width - 1, top + image.height - 1))
            lib.lv_draw_image(layer, dsc, area)
        finally:
            self.pop()


# ---------------------------------------------------------------------------
# Hover tracking: LVGL only reports pointer movement to pressed objects, so
# poll the pointer devices once per loop iteration for canvases that listen.
# ---------------------------------------------------------------------------

_hover = {}
_poller_installed = False


def _ensure_poller():
    global _poller_installed
    if not _poller_installed:
        runtime.pollers.append(_poll_hover)
        _poller_installed = True


def _poll_hover():
    if not _hover:
        return
    screen = lib.lv_screen_active()
    point = ffi.new('lv_point_t *')
    hit = None
    indev = lib.lv_indev_get_next(ffi.NULL)
    while indev != ffi.NULL:
        if lib.lv_indev_get_type(indev) == lib.LV_INDEV_TYPE_POINTER:
            lib.lv_indev_get_point(indev, point)
            hit = lib.lv_indev_search_obj(screen, point)
            break
        indev = lib.lv_indev_get_next(indev)
    if hit is None:
        return
    for entry in list(_hover.values()):
        native = entry['native']
        node = native.node
        if node is None or native.obj is None:
            continue
        inside = hit == native.obj
        area = ffi.new('lv_area_t *')
        lib.lv_obj_get_coords(native.obj, area)
        position = (point.x - area.x1, point.y - area.y1)
        e = PUIEvent()
        e.x, e.y = position
        e.button = 0
        if inside and not entry['inside']:
            node._mouseenter(e)
        if inside and position != entry['point']:
            node._mousemove(e)
        if entry['inside'] and not inside:
            node._mouseleave(e)
        entry['inside'] = inside
        entry['point'] = position if inside else None
