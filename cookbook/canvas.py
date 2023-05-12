from .config import *

class CanvasExample(PUIView):
    def content(self):
        Canvas(self.painter, bgColor=0xFFFFFF)

    @staticmethod
    def painter(canvas):
        canvas.drawText(20, 60, "PUI")
        canvas.drawLine(10,50,50,10, color=0xFFFF00)
        canvas.drawPolyline(((20,20),(30,30),(40,10),(50,50)), color=0xFF0000)
