from __future__ import annotations
import os
import time
from functools import wraps as _wraps
from .. import _typing as _t
from .. import *
from .base import *
from .window import Window, _setup_screen
from ..decorator import _warn_deprecated_decorator


class Application(LPUIView):
    def __init__(self, *args: _t.Any, title: str = '', driver: str | None = None) -> None:
        super().__init__(*args)
        self.title = title
        from . import native
        if driver is None:
            driver = os.environ.get("PUI_LVGL_DRIVER") or native.default_driver
        name = driver.split('#', 1)[0].strip().lower()
        if name not in native.supported_drivers:
            raise RuntimeError(
                f"LVGL driver '{name}' is not in the loaded build {native.build} "
                f"(supports: {', '.join(sorted(native.supported_drivers))}); "
                f"set PUI_LVGL_DRIVER before importing PUI.lvgl or build liblvgl_{name}")
        self._driver = driver
        self._quitting = False

    def redraw(self):
        if self.ui is not None:
            super().redraw()
        else:
            self.sync()

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
        # Declare the content first so the display can be created with the
        # first Window's size: resizing a freshly created X11 window leaves
        # XQuartz drawing the old window's rounded-corner mask.
        super().update(prev)
        if self.ui is None:
            driver, title = self._initial_display()
            if lib.pui_lvgl_init(driver.encode(), text_bytes(title)) != 0:
                raise RuntimeError(f"Failed to initialize LVGL with driver '{self._driver}'")
            self.ui = lib.lv_screen_active()
            runtime.app = self
            _setup_screen(self.ui)

    def _initial_display(self):
        """Driver string sized to the first Window, and the window title."""
        window = None
        stack = list(self.children)
        while stack:
            node = stack.pop(0)
            if isinstance(node, Window):
                window = node
                break
            stack.extend(node.children)
        title = (window.title if window is not None and window.title else self.title) or ''
        parts = self._driver.split('#')
        if any(part.split('=', 1)[0].strip() in ('width', 'height') for part in parts[1:]):
            return self._driver, title  # explicit display size wins
        size = window.preferred_size if window is not None else None
        if size:
            return f'{self._driver}#width={int(size[0])}#height={int(size[1])}', title
        return self._driver, title

    @property
    def inner(self):
        return self.ui

    def addChild(self, idx, child):
        if isinstance(child, Window):
            return
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.lv_obj_move_to_index(child.outer, idx)

    def removeChild(self, idx, child):
        if isinstance(child, Window):
            return
        if isinstance(child, LBaseWidget) and child.ui is not None:
            lib.lv_obj_move_to_index(child.outer, -1)

    def postSync(self):
        if self.ui is not None and not any(isinstance(c, Window) for c in physical_children(self)):
            configure_flex(self, False, True, True)
        super().postSync()

    def run(self, *, codex: _t.AIProvider = None, claude: _t.AIProvider = None, **kwargs):
        if codex is not None:
            kwargs['codex'] = codex
        if claude is not None:
            kwargs['claude'] = claude
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None):
        from ..ai.native import start
        return start(self, 'lvgl', self._mainloop, landlock=landlock, codex=codex, claude=claude)

    def process_events(self):
        """Run queued work and one LVGL tick; returns seconds until more work is due."""
        runtime.run_pending()
        ms = lib.pui_lvgl_timer_handler()
        runtime.poll()
        runtime.run_pending()
        wait = min(ms, 50) / 1000.0
        delay = runtime.next_delay()
        return wait if delay is None else min(wait, delay)

    def _mainloop(self):
        try:
            if self.ui is None:
                self.sync()
            while not self._quitting and lib.pui_lvgl_is_running():
                wait = self.process_events()
                if wait > 0:
                    time.sleep(wait)
        finally:
            self._quit()

    def _quit(self):
        if not self.destroyed:
            from ..dom import recur_delete
            recur_delete(self, self, True)

    def quit(self):
        self._quitting = True
        runtime.post(lambda: None)

    def destroy(self, direct):
        runtime.clear()
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
