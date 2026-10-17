from .base import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
import contextvars


class Application(FView):
    def __init__(self, icon=None, *, title=''):
        super().__init__()
        self.title = title
        self.icon = icon
        self.ready = False
        self.focused_editor = None
        self.loop = None
        self.context = contextvars.copy_context()

    def sync(self):
        if self.ready:
            super().sync()

    async def flet_app(self, page: ft.Page):
        self.ui = page
        self.loop = asyncio.get_running_loop()
        self.context = contextvars.copy_context()
        self.ready = True
        if self.title:
            page.title = self.title
        if self.icon is not None:
            page.window.icon = self.icon
        self.sync()
        from ..ai.native import ready
        ready(self, 'flet')

    def addChild(self, idx, child):
        if idx > 0:
            raise ValueError('Flet supports one Window per application')

    def removeChild(self, idx, child):
        self.ui.controls.clear()

    def run(self, **kwargs):
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex=None, claude=None):
        from ..ai.native import start
        return start(self, 'flet', lambda: ft.run(self.flet_app), landlock=landlock, codex=codex, claude=claude)

    def quit(self):
        if not self.destroyed and self.ready:
            self.ui.run_task(self._quit)

    async def _quit(self):
        page = self.ui
        from ..dom import recur_delete
        recur_delete(self, self, True)
        await page.window.close()


def PUIApp(func):
    """Deprecated: subclass Application and implement content() instead."""
    _warn_deprecated_decorator('PUIApp', 'Application')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIAppWrapper(Application):
            def __init__(self):
                self.name = func.__name__
                super().__init__()

            def content(self):
                return func(*args, **kwargs)
        return PUIAppWrapper()
    return func_wrapper
