from .. import *
from .base import *

class FApplication(PUIView):
    def __init__(self):
        super().__init__()
        self.ready = False

    def update(self, prev=None, redraw=False):
        if not self.ready:
            return
        super().update(redraw=False)

    def flet_app(self, page: ft.Page):
        self.ui = page
        self.ready = True
        self.update()

    def addChild(self, idx, child):
        if idx > 0:
            print("Flet backend only support single window")

    def removeChild(self, idx, child):
        pass

    def start(self):
        ft.app(self.flet_app)
