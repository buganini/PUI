from .view import *
from functools import wraps as _wraps
import warnings as _warnings


def _warn_deprecated_decorator(name, replacement):
    _warnings.warn(
        f'@{name} is deprecated; subclass {replacement} and implement content() instead.',
        DeprecationWarning,
        stacklevel=3,
    )

def PUI(func):
    """
    Deprecated: subclass PUIView and implement content() instead.

    PUI.PUI triggers update() directly by redraw().
    """
    _warn_deprecated_decorator('PUI', 'PUIView')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(PUIView):
            pui_virtual = True
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper
