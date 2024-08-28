from .. import *
from .base import *
import flet.canvas as cv

class Canvas(FBase):
    def __init__(self, painter, *args):
        super().__init__()
        self.ui = None
        self.painter = painter
        self.args = args

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.puinode = self
        else:
            self.ui = cv.Canvas()
        if self.layout_width:
            self.ui.width = self.layout_width
        else:
            self.ui.width = float("inf")
        if self.layout_height:
            self.ui.height = self.layout_height
        else:
            self.ui.height = float("inf")
        self.ui.shapes.clear()
        self.painter(self, *self.args)
        try:
            self.ui.update()
        except:
            pass
        super().update(prev)

    def drawText(self, x, y, text, w=None, h=None, rotate=0, anchor=Anchor.LEFT_TOP):
        if rotate !=0:
            print("drawText: rotate not implemented")
        self.ui.shapes.append(
            cv.Text(
                x,
                y,
                text,
            )
        )

    def drawLine(self, x1, y1, x2, y2, color=None, width=None):
        params = {}
        if not color is None:
            params["color"] = f"#{color:06X}"
        if not width is None:
            params["stroke_width"] = width
        self.ui.shapes.append(
            cv.Line(
                x1,
                y1,
                x2,
                y2,
                ft.Paint(**params, style=ft.PaintingStyle.STROKE)
            ),
        )

    def drawPolyline(self, coords, color=None, width=None):
        params = {}
        if not color is None:
            params["color"] = f"#{color:06X}"
        if not width is None:
            params["stroke_width"] = width
        paint = ft.Paint(**params, style=ft.PaintingStyle.STROKE)
        for i in range(1, len(coords)):
            self.ui.shapes.append(
                cv.Line(
                    coords[i-1][0],
                    coords[i-1][1],
                    coords[i][0],
                    coords[i][1],
                    paint
                ),
            )

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        print("drawPolygon not implemented")

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        print("drawRect not implemented")

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        print("drawEllipse not implemented")
