from .config import *

class CanvasExample(PUIView):
    def content(self):
        Canvas(self.painter).style(bgColor=0xFFFFFF)

    @staticmethod
    def painter(canvas):
        canvas.drawText(20, 60, "PUI")
        canvas.drawLine(20,30,70,80, color=0xFFFF00)
        canvas.drawPolyline([(10,50),(50,10),(70,70),(10,50)], color=0xFF0000)
