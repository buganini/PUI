from .. import *
from .base import *

class Application(PUIView):
    def __init__(self):
        super().__init__()
        self.ready = False

    def update(self, prev=None):
        if not self.ready:
            return
        super().update(prev)

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

def PUIApp(func):
    def func_wrapper(*args, **kwargs):
        class PUIAppWrapper(Application):
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIAppWrapper(func.__name__)
        return ret

    return func_wrapper
