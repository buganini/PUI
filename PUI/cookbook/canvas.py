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

            Canvas(self.painter, self.state).style(bgColor=0x1C2A30).layout(width=100, height=100)
            Spacer()

    def rotate(self, e, delta):
        self.state.rotate += delta

    @staticmethod
    def painter(canvas, state):
        canvas.drawText(50, 50, "___", color=0xFFF7E6)
        canvas.drawText(50, 50, "PUI", rotate=state.rotate, anchor=Anchor.CENTER, color=0xFFF7E6)
        canvas.drawLine(20,30,70,80, color=0xD3B98B)
        canvas.drawPolyline([(10,50),(50,10),(70,70),(10,50)], color=0x8FA38A)
        if PUI_BACKEND in ("PySide6", "wx", "flet", "web", "pyodide"):
            canvas.drawCubicBezier(
                (10,80), (25,20), (75,80), (90,20),
                color=0x366C91,
                width=2,
            )
        canvas.drawRect(10,10,20,20, fill=0xF2E6CF, stroke=0x366C91, width=2)
