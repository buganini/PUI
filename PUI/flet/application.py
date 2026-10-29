from __future__ import annotations
from .. import _typing as _t
from .base import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
import contextvars
from concurrent.futures import ThreadPoolExecutor


class Application(FView):
    def __init__(self, icon: _t.Any = None, *, title: str = '') -> None:
        super().__init__()
        self.title = title
        self.icon = icon
        self.ready = False
        self.focused_editor = None
        self.loop = None
        self.context = contextvars.copy_context()
        self._stopping = False
        self._modal_stack = []
        self._dialogs = {}
        self._dialog_tasks = set()

    def sync(self):
        if self.ready:
            super().sync()

    async def flet_app(self, page: ft.Page):
        self.ui = page
        self.loop = asyncio.get_running_loop()
        self.context = contextvars.copy_context()
        self._callback_queue = asyncio.Queue()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='pui-flet-callback')
        self._callback_task = asyncio.create_task(self._callbacks())
        page.on_keyboard_event = self._on_keyboard_event
        page.on_close = self._shutdown
        page.on_disconnect = self._shutdown
        self.ready = True
        if self.title:
            page.title = self.title
        if self.icon is not None:
            page.window.icon = self.icon
        self.sync()
        from ..ai.native import ready
        ready(self, 'flet')

    async def _on_keyboard_event(self, event):
        # Do not dismiss a declarative modal beneath an imperative dialog/picker.
        if (event.key == 'Escape' and not self._stopping and not self._dialogs
                and self._modal_stack):
            dialog = self._modal_stack[-1]
            if dialog.open:
                dialog._pui_modal_node.get_node()._dismiss()

    def enqueue_callback(self, callback, *args, **kwargs):
        def enqueue():
            if not self._stopping:
                self._callback_queue.put_nowait((callback, args, kwargs))
        self.loop.call_soon_threadsafe(enqueue, context=self.context.copy())

    async def _callbacks(self):
        from .dialog import callback_app
        while True:
            job = await self._callback_queue.get()
            if job is None or self._stopping:
                self._callback_queue.task_done()
                return
            callback, args, kwargs = job
            def invoke():
                token = callback_app.set(self)
                try:
                    return callback(*args, **kwargs)
                finally:
                    callback_app.reset(token)
            try:
                await self.loop.run_in_executor(self._executor, self.context.copy().run, invoke)
            except Exception as error:
                self.loop.call_exception_handler({'message': 'PUI Flet callback failed', 'exception': error})
            finally:
                self._callback_queue.task_done()

    async def _shutdown(self, event=None):
        if self._stopping:
            return
        self._stopping = True
        for future, kind in list(self._dialogs.items()):
            if not future.done():
                future.set_result(False if kind == 'confirm' else None)
        tasks = list(self._dialog_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._callback_queue.put_nowait(None)
        await self._callback_task
        self._executor.shutdown(wait=True)

    def addChild(self, idx, child):
        if idx > 0:
            raise ValueError('Flet supports one Window per application')

    def removeChild(self, idx, child):
        self.ui.controls.clear()

    def run(self, *, codex: _t.AIProvider = None, claude: _t.AIProvider = None, **kwargs):
        if codex is not None:
            kwargs['codex'] = codex
        if claude is not None:
            kwargs['claude'] = claude
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None):
        from ..ai.native import start
        return start(self, 'flet', lambda: ft.run(self.flet_app), landlock=landlock, codex=codex, claude=claude)

    def quit(self):
        if not self.destroyed and self.ready:
            self.ui.run_task(self._quit)

    async def _quit(self):
        page = self.ui
        await self._shutdown()
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
