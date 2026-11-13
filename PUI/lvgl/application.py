from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
import os
import time
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator


class Application(LPUIView):
    def __init__(self, *args: _t.Any, title: str = '', driver: str = None) -> None:
        super().__init__(*args)
        self.title = title
        if driver is None:
            driver = os.environ.get("PUI_LVGL_DRIVER", "sdl2")
        self._driver = driver
        self._command_handles = []

    def _post_command(self, callback):
        self._command_handles.append(callback)

    def _post_timer(self, delay, callback):
        handle = ffi.new_handle(callback)
        self._command_handles.append(handle)
        lib.pui_lv_timer_create(lib._pui_timer_cb, int(delay * 1000), handle)

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
        if self.ui is None:
            if lib.pui_lvgl_init(self._driver.encode()) != 0:
                raise RuntimeError(f"Failed to initialize LVGL with driver '{self._driver}'")
            self.ui = lib.pui_lvgl_screen_active()
        super().update(prev)

    @property
    def inner(self):
        return self.ui

    def addChild(self, idx, child):
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.pui_lv_obj_move_to_index(child.outer, idx)
            if not child.layout_width:
                lib.pui_lv_obj_set_width_pct(child.outer, 100)
            if not child.layout_height:
                lib.pui_lv_obj_set_height_pct(child.outer, 100)

    def removeChild(self, idx, child):
        pass

    def run(self, *, codex: _t.AIProvider = None, claude: _t.AIProvider = None, **kwargs):
        if codex is not None:
            kwargs['codex'] = codex
        if claude is not None:
            kwargs['claude'] = claude
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None):
        from ..ai.native import start
        return start(self, 'lvgl', self._mainloop, landlock=landlock, codex=codex, claude=claude)

    def _mainloop(self):
        try:
            self.sync()
            while lib.pui_lvgl_is_running():
                # Process queued Python commands.
                commands = self._command_handles[:]
                self._command_handles.clear()
                for cmd in commands:
                    if callable(cmd):
                        try:
                            cmd()
                        except Exception:
                            import traceback
                            traceback.print_exc()

                ms = lib.pui_lvgl_timer_handler()
                if ms > 0:
                    time.sleep(ms / 1000.0)
        finally:
            self._quit()

    def _quit(self):
        if not self.destroyed:
            from ..dom import recur_delete
            recur_delete(self, self, True)

    def quit(self):
        if not self.destroyed:
            self._quit()

    def destroy(self, direct):
        self._command_handles.clear()
        super().destroy(direct)
        lib.pui_lvgl_deinit()


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
