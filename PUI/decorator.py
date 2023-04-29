from .view import *

def PUI(func):
    def func_wrapper(*args):
        class PUIViewWrapper(PUIView):
            def content(self):
                return self.__wrapped_content__()

            def __wrapped_content__(self):
                return func(*args)
        ret = PUIViewWrapper()
        ret.name = func.__name__
        return ret

    return func_wrapper