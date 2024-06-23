from .config import *

class CanvasExample(PUIView):
    def content(self):
        with VBox():
            Canvas(self.painter).style(bgColor=0x555555).layout(width=100, height=100)
            Spacer()

    @staticmethod
    def painter(canvas):
        canvas.drawText(20, 60, "PUI")
        canvas.drawLine(20,30,70,80, color=0xFFFF00)
        canvas.drawPolyline([(10,50),(50,10),(70,70),(10,50)], color=0xFF0000)
        canvas.drawRect(10,10,20,20, fill=0xCCCCCC, stroke=0xFF00FF, width=2)