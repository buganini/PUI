from __future__ import annotations
from pathlib import Path
from .. import _typing as _t
from .base import *


class Button(LBaseWidget):
    _default_size = ('content', 'content')
    _always_clickable = True

    def __init__(self, text: _t.Any = '', *, icon: _t.Any = None, disabled: bool = False) -> None:
        super().__init__()
        self.text = str(text)
        self.icon = icon
        self.disabled = disabled
        self._tag = self.icon or self.text

    def create(self, parent):
        obj = lib.lv_button_create(parent)
        lib.lv_obj_set_flex_flow(obj, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(obj, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        lib.lv_obj_set_style_pad_column(obj, 6, SEL)
        return obj

    def configure(self, prev):
        obj = self.ui
        store = self._native.store
        lib.lv_obj_set_state(obj, lib.LV_STATE_DISABLED, bool(self.disabled))
        icon = str(Path(self.icon)) if self.icon is not None else None
        image = store.get('icon')
        if icon is None and image is not None:
            lib.lv_obj_delete(image)
            image = store['icon'] = None
            store['icon_path'] = None
        if icon is not None:
            if image is None:
                image = store['icon'] = lib.lv_image_create(obj)
                lib.lv_obj_move_to_index(image, 0)
                lib.lv_obj_remove_flag(image, lib.LV_OBJ_FLAG_CLICKABLE)
            if store.get('icon_path') != icon:
                lib.lv_image_set_src(image, ('A:' + icon).encode())
                store['icon_path'] = icon
                w = lib.lv_image_get_src_width(image)
                h = lib.lv_image_get_src_height(image)
                side = 20
                if w > 0 and h > 0:
                    scale = side / max(w, h)
                    lib.lv_obj_set_size(image, max(1, round(w * scale)), max(1, round(h * scale)))
                    lib.lv_image_set_inner_align(image, lib.LV_IMAGE_ALIGN_CONTAIN)
                    lib.lv_image_set_antialias(image, True)
        label = store.get('label')
        if self.text or icon is None:
            if label is None:
                label = store['label'] = lib.lv_label_create(obj)
            lib.lv_label_set_text(label, text_bytes(self.text))
        elif label is not None:
            lib.lv_obj_delete(label)
            store['label'] = None
