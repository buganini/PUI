from __future__ import annotations
import math
from .. import _typing as _t
from .base import *


class Scroll(LBaseWidget):
    pui_terminal = False
    END = -0.0
    _default_size = ('content', 'content')
    _lv_events = (lib.LV_EVENT_SCROLL_END, lib.LV_EVENT_SIZE_CHANGED)

    def __init__(self, vertical: bool | None = None, horizontal: bool | None = False) -> None:
        super().__init__()
        self.vertical = vertical
        self.horizontal = horizontal
        self._targets = [None, None]  # (from_end, offset) per axis

    def _base_expansion_priority(self, axis):
        enabled = self.horizontal if axis == 'x' else self.vertical
        return 1 if enabled is False else 4

    def scrollX(self, pos=0):
        self._targets[0] = (math.copysign(1, pos) < 0, abs(pos))
        return self

    def scrollY(self, pos=0):
        self._targets[1] = (math.copysign(1, pos) < 0, abs(pos))
        return self

    def adopt(self, prev):
        # Keep the user's position, measured from the edge they scrolled to.
        store = self._native.store
        anchor = store.get('anchor') or [None, None]
        for axis in (0, 1):
            if anchor[axis] is not None:
                self._targets[axis] = anchor[axis]

    def configure(self, prev):
        obj = self.ui
        lib.lv_obj_set_style_pad_all(obj, 0, SEL)
        lib.lv_obj_set_style_radius(obj, 0, SEL)
        h = self.horizontal is not False
        v = self.vertical is not False
        lib.lv_obj_set_scroll_dir(obj, (lib.LV_DIR_HOR if h else 0) | (lib.LV_DIR_VER if v else 0))
        forced = self.horizontal is True or self.vertical is True
        lib.lv_obj_set_scrollbar_mode(obj, lib.LV_SCROLLBAR_MODE_OFF if not (h or v)
                                      else lib.LV_SCROLLBAR_MODE_ON if forced else lib.LV_SCROLLBAR_MODE_AUTO)
        lib.lv_obj_set_flex_flow(obj, lib.LV_FLEX_FLOW_COLUMN)

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_SCROLL_END:
            self._record_anchor()
        elif code == lib.LV_EVENT_SIZE_CHANGED:
            lib.lv_obj_stop_scroll_anim(self.ui)
            lib.lv_obj_readjust_scroll(self.ui, lib.LV_ANIM_OFF)
            self._native.store['dirty_anchor'] = True
            runtime.post(self._restore)
            super()._lv_event(code, e)
        else:
            super()._lv_event(code, e)

    def _record_anchor(self):
        obj = self.ui
        anchor = []
        for start, end in ((lib.lv_obj_get_scroll_x(obj), lib.lv_obj_get_scroll_right(obj)),
                           (lib.lv_obj_get_scroll_y(obj), lib.lv_obj_get_scroll_bottom(obj))):
            anchor.append((True, max(0, end)) if end < 10 and start > 0 else (False, max(0, start)))
        self._native.store['anchor'] = anchor

    def postSync(self):
        if self.ui is not None:
            for child in physical_children(self):
                # A disabled axis fits the content to the viewport: at least
                # the viewport size, but the scroll area follows the content.
                for horizontal, enabled, explicit in ((True, self.horizontal, child.layout_width),
                                                      (False, self.vertical, child.layout_height)):
                    minimum = lib.lv_obj_set_style_min_width if horizontal else lib.lv_obj_set_style_min_height
                    if enabled is False and explicit is None:
                        minimum(child.outer, lib.lv_pct(100), SEL)
                        child._native.store['scroll_min_' + str(horizontal)] = True
                    elif child._native.store.pop('scroll_min_' + str(horizontal), False):
                        lib.lv_obj_remove_local_style_prop(
                            child.outer, lib.LV_STYLE_MIN_WIDTH if horizontal else lib.LV_STYLE_MIN_HEIGHT, SEL)
                        child._apply_styles()
                    release_dim(child, horizontal)
                hook = getattr(child, '_relayout', None)
                if hook is not None:
                    hook()
            self._native.store['anchor'] = list(self._targets)
            runtime.post(self._restore)
        super().postSync()

    def _restore(self):
        node = self.get_node()
        obj = node.ui
        if obj is None or node.destroyed:
            return
        lib.lv_obj_update_layout(obj)
        anchor = node._native.store.get('anchor') or [None, None]
        x, y = lib.lv_obj_get_scroll_x(obj), lib.lv_obj_get_scroll_y(obj)
        targets = []
        for target, pos, end in ((anchor[0], x, lib.lv_obj_get_scroll_right(obj)),
                                 (anchor[1], y, lib.lv_obj_get_scroll_bottom(obj))):
            if target is None:
                targets.append(pos)
            elif target[0]:
                targets.append(max(0, pos + end - int(target[1])))
            else:
                targets.append(int(target[1]))
        if targets != [x, y]:
            lib.lv_obj_scroll_to(obj, targets[0], targets[1], lib.LV_ANIM_OFF)
