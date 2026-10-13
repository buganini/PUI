from .. import *
from .base import *
from functools import wraps as _wraps

class Application(TPUIView):
    def __init__(self, *args):
        super().__init__(*args)
        self.theme = None

    def tkinter(self, theme=None, **kwargs):
        super().tkinter(**kwargs)
        self.theme = theme
        return self

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
        if self.ui is None:
            self.ui = tk.Tk()
            ttkStyle = ttk.Style(self.ui)
            if self.theme:
                ttkStyle.theme_use(self.theme)
            self.ui.withdraw()

        super().update(prev)

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def quit(self):
        if not self.destroyed and self.ui is not None:
            self.ui.after(0, self._quit)

    def _quit(self):
        if not self.destroyed:
            from ..dom import recur_delete
            recur_delete(self, self, True)

    def start(self):
        self.ui.mainloop()


def PUIApp(func):
    @_wraps(func)
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
