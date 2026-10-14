from pathlib import Path
from PUI.web import Application, Window, VBox, Button, Image, Canvas, ImageResource, State


class App(Application):
    def setup(self):
        self.state = State()
        self.state.visible = True
        self.path = Path(__file__).with_name('web-image.png')

    def content(self):
        with Window():
            with VBox():
                Button('Toggle images').click(self.toggle)
                if self.state.visible:
                    Image(self.path).layout(width=80, height=40)
                    Canvas(self.paint).layout(width=120, height=80)

    def toggle(self, event):
        self.state.visible = not self.state.visible

    def paint(self, c):
        image = ImageResource.load(self.path)
        c.drawImage(image, width=40, height=20)
        c.drawImage(image.crop(2, 0, 2, 2).scale(20, 20, quality=0), x=50, y=0)
        c.drawImage(image.scale(20, 20).crop(0, 0, 10, 10), x=80, y=0, opacity=.5)
