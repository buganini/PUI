from .config import *

class DropExample(PUIView):
    def content(self):
        with VBox():
            Label("DROP HERE").style(fontSize=72).dragEnter(self.handleDragEnter).drop(self.handleDrop)
            Spacer()

    def handleDragEnter(self, event):
        print("DragEnter", event)
        event.accept()

    def handleDrop(self, event):
        print("Dropped", event)
        if event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            print("Dropped files", files)
            event.accept()
        else:
            event.ignore()

