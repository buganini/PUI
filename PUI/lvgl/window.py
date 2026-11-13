from __future__ import annotations
from .. import _typing as _t
from .base import *


def _setup_screen(obj):
    lib.lv_obj_set_flex_flow(obj, lib.LV_FLEX_FLOW_COLUMN)
    lib.lv_obj_set_style_pad_all(obj, 0, SEL)
    lib.lv_obj_set_style_pad_row(obj, 0, SEL)
    lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)


class Window(LBaseWidget):
    """The display's active screen; the display hosts a single window."""
    pui_terminal = False

    def __init__(self, title: str | None = None, icon: _t.Any = None, size: tuple[int, int] | None = None,
                 maximize: bool | None = None, fullscreen: bool | None = None) -> None:
        super().__init__()
        self.title = title
        self.icon = icon
        self.preferred_size = size

    def maximize(self, enabled=True):
        return self

    def fullscreen(self, enabled=True):
        return self

    def create(self, parent):
        return lib.lv_screen_active()

    def configure(self, prev):
        _setup_screen(self.ui)
        title = self.title
        if title is None:
            app = self.root
            while app is not None and app.parent is not app:
                app = app.parent
            title = getattr(app, 'title', None)
        if title and (prev is None or prev.title != self.title):
            lib.pui_lvgl_set_title(text_bytes(title))
        size = self.preferred_size
        if size and (prev is None or prev.preferred_size != size):
            lib.pui_lvgl_set_size(int(size[0]), int(size[1]))

    def _apply_dim(self, horizontal):
        pass  # the screen always covers the display

    def _apply_styles(self):
        visible, self._visible = self._visible, True
        try:
            super()._apply_styles()
        finally:
            self._visible = visible

    def postSync(self):
        if self.ui is not None:
            from .menu import MenuBar
            # Out-of-order menu bars sit above the content, outside the flex
            # distribution of the window's children.
            for child in self.children:
                child = child.get_node()
                if isinstance(child, MenuBar) and child.ui is not None:
                    lib.lv_obj_move_to_index(child.ui, 0)
            configure_flex(self, False, True, True)
        super().postSync()

    def destroy(self, direct):
        native = self._native
        if native is not None:
            native.node = None
            # The display owns its screen; only remove our content.
            if direct and native.obj is not None:
                lib.lv_obj_clean(native.obj)
                lib.lv_obj_remove_event_cb_with_user_data(native.obj, lib._pui_event_cb, native.handle)
        self._native = None
        self.ui = None
        PUINode.destroy(self, direct)
