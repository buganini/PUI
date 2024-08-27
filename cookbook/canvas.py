from .config import *

class CanvasExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.rotate = 15

    def content(self):
        with VBox():
            with HBox():
                Label(f"Rotate: {self.state.rotate}")
                Button("+").click(self.rotate, 15)

            Canvas(self.painter, self.state).style(bgColor=0x555555).layout(width=100, height=100)
            Spacer()

    def rotate(self, e, delta):
        self.state.rotate += delta

    @staticmethod
    def painter(canvas, state):
        canvas.drawText(50, 50, "___")
        canvas.drawText(50, 50, "PUI", rotate=state.rotate, anchor=Anchor.CENTER)
        canvas.drawLine(20,30,70,80, color=0xFFFF00)
        canvas.drawPolyline([(10,50),(50,10),(70,70),(10,50)], color=0xFF0000)
        canvas.drawRect(10,10,20,20, fill=0xCCCCCC, stroke=0xFF00FF, width=2)