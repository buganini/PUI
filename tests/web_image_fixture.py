from pathlib import Path
from PUI.web import Application, Window, VBox, Button, Image, Canvas, ImageResource, State


class App(Application):
    def setup(self):
        self.state = State()
        self.state.visible = True
        self.state.highlight = False
        self.path = Path(__file__).with_name('web-image.png')

    def content(self):
        with Window():
            with VBox():
                Button('Toggle images').click(self.toggle)
                Button('Repaint').click(self.repaint)
                if self.state.visible:
                    Image(self.path).layout(width=80, height=40)
                    Canvas(self.paint, self.state.highlight).layout(width=120, height=80)

    def toggle(self, event):
        self.state.visible = not self.state.visible

    def repaint(self, event):
        self.state.highlight = not self.state.highlight

    def paint(self, c, highlight):
        for x in range(10):
            c.drawLine(x, 70, x, 75, color=0)
        image = ImageResource.load(self.path)
        c.drawImage(image, width=40, height=20)
        c.drawImage(image.crop(2, 0, 2, 2).scale(20, 20, quality=0), x=50, y=0)
        c.drawImage(image.scale(20, 20).crop(0, 0, 10, 10), x=80, y=0, opacity=.5)
        c.drawRect(110, 60, 120, 70, fill=0x00ff00 if highlight else 0xff0000)
