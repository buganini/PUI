"""Non-blocking modal dialog drawn on LVGL's top layer."""
from __future__ import annotations
from .._modal import ModalMixin
from .base import *
from .overlay import create_dialog, Handlers


class Modal(ModalMixin, LBaseWidget):
    def create(self, parent):
        size = self.preferred_size or (None, None)
        fill = self._initial_maximize or self._initial_fullscreen
        backdrop, panel, body, close = create_dialog(
            self.title or '', width=None if fill else size[0], height=None if fill else size[1], on_close=True)
        if fill:
            lib.lv_obj_set_size(panel, lib.lv_pct(100), lib.lv_pct(100))
            lib.lv_obj_set_width(body, lib.lv_pct(100))
            lib.lv_obj_set_flex_grow(body, 1)
        lib.lv_obj_add_flag(backdrop, lib.LV_OBJ_FLAG_HIDDEN)
        self._pending = {'body': body, 'panel': panel, 'close': close}
        return backdrop

    def configure(self, prev):
        store = self._native.store
        if 'body' not in store:
            store.update(self._pending)
            handlers = store['handlers'] = Handlers()
            handlers.on(store['close'], lib.LV_EVENT_CLICKED,
                        lambda code, e: runtime.post(self.get_node()._dismiss))
            store['on_delete'] = [handlers.clear]
            # The title label is the first child of the title bar.
        bar = lib.lv_obj_get_child(store['panel'], 0)
        lib.lv_label_set_text(lib.lv_obj_get_child(bar, 0), text_bytes(self.title or ''))

    @property
    def inner(self):
        return self._native.store.get('body') if self._native is not None else None

    def _apply_dim(self, horizontal):
        pass  # the backdrop always covers the screen

    def _apply_styles(self):
        super()._apply_styles()
        self._show(self._modal_state['open'])

    def _show(self, opened):
        if self.ui is None:
            return
        if opened:
            lib.lv_obj_remove_flag(self.ui, lib.LV_OBJ_FLAG_HIDDEN)
        else:
            lib.lv_obj_add_flag(self.ui, lib.LV_OBJ_FLAG_HIDDEN)

    def _set_modal(self, opened):
        if self.ui is None or self._modal_state['open'] == opened:
            return
        self._show(opened)
        self._transition(opened)

    def postSync(self):
        if self.ui is not None:
            sized = bool(self.preferred_size or self._initial_maximize or self._initial_fullscreen)
            configure_flex(self, False, sized, sized)
        super().postSync()
