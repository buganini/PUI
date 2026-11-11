from .config import *
from pathlib import Path

class ImageExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.clicks = 0

    def content(self):
        with VBox():
            path = Path(__file__).with_name("assets") / "windmill.jpg"
            Image(str(path)).layout(width=400).click(self.on_click)
            Label("The Windmill at Wijk bij Duurstede")
            Label("Jacob van Ruisdael, c. 1668–1670")
            Label("Rijksmuseum, Amsterdam · Public Domain")
            Label("https://id.rijksmuseum.nl/200107959")
            Label(f"Clicked: {self.state.clicks}")
            Spacer()

    def on_click(self, event):
        self.state.clicks += 1
