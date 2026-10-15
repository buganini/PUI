from .. import *
from .base import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator

class Application(TPUIView):
    def __init__(self, *args, title=''):
        super().__init__(*args)
        self.title = title
        self.theme = None
        self._windows = set()
        self._window_check_id = None
        self._quit_id = None

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

        if self.title:
            self.ui.title(self.title)
        super().update(prev)

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def _register_window(self, window):
        self._windows.add(window)
        window.protocol('WM_DELETE_WINDOW', lambda: self._close_window(window))
        window.bind('<Destroy>', lambda event: self._window_destroyed(window, event), add='+')

    def _close_window(self, window):
        if self.destroyed or window not in self._windows:
            return
        # Like Qt, retain a closed window's controls across redraws while other
        # windows remain open. The last close tears down the entire application.
        window.withdraw()
        self._windows.remove(window)
        self._check_windows_later()

    def _window_destroyed(self, window, event):
        if event.widget is window and not self.destroyed:
            self._windows.discard(window)
            self._check_windows_later()

    def _check_windows_later(self):
        if self._window_check_id is None:
            # Reconciliation may replace the last window in the same update.
            self._window_check_id = self.ui.after(0, self._quit_if_no_windows)

    def _quit_if_no_windows(self):
        self._window_check_id = None
        if not self._windows:
            self._quit()

    def quit(self):
        if not self.destroyed and self.ui is not None and self._quit_id is None:
            self._quit_id = self.ui.after(0, self._quit)

    def _quit(self):
        if not self.destroyed:
            from ..dom import recur_delete
            recur_delete(self, self, True)

    def start(self):
        try:
            self.ui.mainloop()
        finally:
            self._quit()

    def destroy(self, direct):
        for attribute in ('_window_check_id', '_quit_id'):
            token = getattr(self, attribute)
            if token is not None:
                self.ui.after_cancel(token)
                setattr(self, attribute, None)
        self._windows.clear()
        super().destroy(direct)


def PUIApp(func):
    """Deprecated: subclass Application and implement content() instead."""
    _warn_deprecated_decorator('PUIApp', 'Application')
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
