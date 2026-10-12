from .base import *
import math
import flet.canvas as cv


class Canvas(FBase):
    pui_terminal = True

    def __init__(self, painter, *args):
        super().__init__()
        self.painter, self.args = painter, args
        self.pixel_density = 1.0
        self.width = self.height = 0

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui = prev.ui
            self.width, self.height = prev.width, prev.height
        else:
            self.ui = cv.Canvas()
        self.ui.width, self.ui.height = self.layout_width, self.layout_height
        self.width = self.layout_width if self.layout_width is not None else self.width
        self.height = self.layout_height if self.layout_height is not None else self.height
        self.ui.on_resize = self.on_resize
        super().update(prev)
        self.paint(notify=False)

    def on_resize(self, event):
        node = self.get_node()
        if not node.destroyed:
            node.width, node.height = event.width, event.height
            node.paint()

    def paint(self, notify=True):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        node.ui.shapes.clear()
        immediate = node.painter(node, *node.args)
        app = FView.application(node)
        if app is not None and app.ready:
            if notify:
                app.ui.update()
            if immediate:
                app.loop.call_soon(node.paint, context=app.context.copy())

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
                                         ft.Paint(color=colour(color), stroke_width=width,
                                                  style=ft.PaintingStyle.STROKE)))

    def drawPolyline(self, coords, color=None, width=1):
        coords = list(coords)
        if color is None or len(coords) < 2:
            return
        elements = [cv.Path.MoveTo(*coords[0])] + [cv.Path.LineTo(*point) for point in coords[1:]]
        self.ui.shapes.append(cv.Path(elements=elements,
                                     paint=ft.Paint(color=colour(color), stroke_width=width,
                                                    style=ft.PaintingStyle.STROKE)))

    def drawCubicBezier(self, start, control1, control2, end, color=None, width=1):
        if color is not None:
            self.ui.shapes.append(cv.Path(elements=[cv.Path.MoveTo(*start),
                                                   cv.Path.CubicTo(*control1, *control2, *end)],
                                         paint=ft.Paint(color=colour(color), stroke_width=width,
                                                        style=ft.PaintingStyle.STROKE)))

    def shape(self, constructor, fill, stroke, width):
        if fill is not None:
            self.ui.shapes.append(constructor(ft.Paint(color=colour(fill), style=ft.PaintingStyle.FILL)))
        if stroke is not None:
            self.ui.shapes.append(constructor(ft.Paint(color=colour(stroke), stroke_width=width,
                                                        style=ft.PaintingStyle.STROKE)))

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
