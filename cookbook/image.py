from .config import *
from pathlib import Path

class ImageExample(PUIView):
    def content(self):
        with VBox():
            path = Path(__file__).with_name("assets") / "windmill.jpg"
            Image(str(path)).layout(width=400)
            Label("The Windmill at Wijk bij Duurstede")
            Label("Jacob van Ruisdael, c. 1668–1670")
            Label("Rijksmuseum, Amsterdam · Public Domain")
            Label("https://id.rijksmuseum.nl/200107959")
            Spacer()
