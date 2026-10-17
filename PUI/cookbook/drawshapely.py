from .config import *

class DrawShapelyExample(PUIView):
    def content(self):
        with VBox():
            Canvas(self.painter).style(bgColor=0x555555).layout(width=500, height=500)
            Spacer()

    @staticmethod
    def painter(canvas):
        from shapely import GeometryCollection, LineString, LinearRing, Point, Polygon
        p = Point(250, 250)
        l = LineString([(100, 30), (200, 30)])
        lr = LinearRing(((10, 10), (10, 50), (50 ,50), (50 , 10)) )
        poly = Polygon(((60, 60), (60, 450), (450 ,450), (450 , 60)), holes=[((80, 80), (80, 100), (100 ,100), (100 , 80))])
        gc = GeometryCollection([p, l, lr, poly])
        canvas.drawShapely(gc, fill=0x000000, stroke=0x00FF00, width=5)
