from .view import *

def PUI(func):
    class PUIViewWrapper(PUIView):
        def content(self):
            return func()

    return PUIViewWrapper