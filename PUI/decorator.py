from .view import *

def PUI(func):
    class PUIViewWrapper(PUIView):
        def content(self):
            return self.__wrapped_content__()

        def __wrapped_content__(self):
            return func()

    return PUIViewWrapper