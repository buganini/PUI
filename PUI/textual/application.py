from __future__ import annotations
from .. import _typing as _t
from typing import Type
import sys
import asyncio
import contextvars
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from textual.driver import Driver
from .. import *
from .base import *
from textual.app import App, CSSPathType, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Checkbox, Input, RadioButton, Tabs

class PUITextualApp(App):

    def __init__(self, puiview, driver_class: Type[Driver] = None, css_path: CSSPathType = None, watch_css: bool = False):
        super().__init__(driver_class, css_path, watch_css)
        self.puiview = puiview
        # Capture the launch stream before Textual redirects stdout during run().
        self._title_console = Console(file=sys.stdout)
        if puiview.title:
            self.title = puiview.title

    def on_mount(self) -> None:
        self._pui_loop = asyncio.get_running_loop()
        self._pui_queue = asyncio.Queue()
        self._pui_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='pui-textual-callback')
        self._pui_dialogs = {}
        self._pui_redraws = {}
        self._pui_busy = self._pui_stopping = False
        self._pui_callback_task = asyncio.create_task(self._callbacks())
        if self.puiview.title and not self.is_headless:
            title = ''.join(character for character in self.puiview.title if character.isprintable())
            self._title_console.set_window_title(title)
        self.puiview.redraw()

    def enqueue_callback(self, callback, *args, **kwargs):
        def enqueue():
            if not self._pui_stopping:
                self._pui_queue.put_nowait((callback, args, kwargs))
        self._pui_loop.call_soon_threadsafe(enqueue)

    async def _callbacks(self):
        from .dialog import callback_app
        while True:
            job = await self._pui_queue.get()
            if job is None or self._pui_stopping:
                return
            callback, args, kwargs = job
            self._pui_busy = True
            context = contextvars.copy_context()
            def invoke():
                token = callback_app.set(self)
                try:
                    return callback(*args, **kwargs)
                finally:
                    callback_app.reset(token)
            try:
                await self._pui_loop.run_in_executor(self._pui_executor, context.run, invoke)
            except Exception as error:
                self._handle_exception(error)
            finally:
                self._pui_busy = False
                self._flush_redraws()

    def request_redraw(self, callback):
        def schedule():
            if not self._pui_stopping:
                self._pui_redraws[callback] = None
                if not self._pui_busy:
                    self._flush_redraws()
        self._pui_loop.call_soon_threadsafe(schedule)

    def _flush_redraws(self):
        callbacks = list(self._pui_redraws)
        self._pui_redraws.clear()
        if not self._pui_stopping:
            for callback in callbacks:
                self.call_next(callback)

    async def on_unmount(self):
        self._pui_stopping = True
        for future, kind in list(self._pui_dialogs.items()):
            if not future.done():
                future.set_result(False if kind == 'confirm' else None)
        self._pui_queue.put_nowait(None)
        await self._pui_callback_task
        self._pui_executor.shutdown(wait=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.button.puinode.get_node()._clicked()

    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
        event.radio_button.puinode.get_node()._changed(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.puinode.get_node()._tchanged(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.puinode.get_node()._tsubmitted(event.value)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.checkbox.puinode.get_node()._changed(event.value)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        event.tabs.puinode.get_node()._tab_activated(event)

    def compose(self) -> ComposeResult:
        yield Vertical(id="frame")

class Application(TPUIView):
    def _observe_size(self):
        from .adaptive import observe
        return observe(self, self.ui.query_one('#frame'))

    def __init__(self, *, title: str = '') -> None:
        super().__init__()
        self.title = title
        self.ui = PUITextualApp(self)

    def addChild(self, idx, child):
        if idx>0:
            raise RuntimeError("Textual backend only support single window")
        self.ui.query_one("#frame").mount(child.outer)

    def redraw(self):
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        self.ui.request_redraw(self._redraw)

    def _redraw(self):
        with self.ui.batch_update():
            self.sync()
        self.updating = False

    def run(self, *, codex: _t.AIProvider = None, claude: _t.AIProvider = None, **kwargs):
        # self.redraw() # need to be after on_mount
        if codex is not None:
            kwargs['codex'] = codex
        if claude is not None:
            kwargs['claude'] = claude
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None):
        from ..ai import unsupported
        unsupported('textual', codex, claude)
        from .._landlock import apply
        apply(landlock)
        self.ui.run()


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
