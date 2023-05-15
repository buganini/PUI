from .view import *

def PUI(func):
    """
    PUI.PUI triggers update() directly by redraw()
    """
    def func_wrapper(*args):
        class PUIViewWrapper(PUIView):
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args)

            @property
            def inner(self):
                return self.parent.inner

            @property
            def outer(self):
                if self.children:
                    return self.children[0].outer
                else:
                    return None

        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper