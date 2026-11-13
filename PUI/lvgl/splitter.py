from __future__ import annotations
from .base import *
from .base import _Native

_HANDLE = 8


class Splitter(LBaseWidget):
    """Panes separated by draggable handles."""
    expand_x_prio = expand_y_prio = 3
    pui_terminal = False
    pui_reflow_children = True
    _default_size = ('content', 'content')
    _lv_events = (lib.LV_EVENT_SIZE_CHANGED,)

    def __init__(self, vertical=False):
        super().__init__()
        self.vertical = vertical

    def configure(self, prev):
        obj = self.ui
        lib.lv_obj_set_style_bg_opa(obj, lib.LV_OPA_TRANSP, SEL)
        lib.lv_obj_set_style_border_width(obj, 0, SEL)
        lib.lv_obj_set_style_radius(obj, 0, SEL)
        lib.lv_obj_set_style_pad_all(obj, 0, SEL)
        lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
        store = self._native.store
        for native in store.get('handles', ()):
            native.node = self
        if store.get('vertical') != self.vertical:
            store['vertical'] = self.vertical
            store['fractions'] = None

    def _panes(self):
        return list(physical_children(self, include_hidden=False))

    def postSync(self):
        if self.ui is None:
            return super().postSync()
        store = self._native.store
        panes = self._panes()
        handles = store.setdefault('handles', [])
        while len(handles) > max(0, len(panes) - 1):
            native = handles.pop()
            if native.obj is not None:
                lib.lv_obj_delete(native.obj)
        while len(handles) < len(panes) - 1:
            obj = lib.lv_obj_create(self.ui)
            lib.lv_obj_remove_style_all(obj)
            lib.lv_obj_set_style_bg_color(obj, lib.lv_color_hex(0x9E9E9E), SEL)
            lib.lv_obj_set_style_bg_opa(obj, lib.LV_OPA_40, SEL)
            lib.lv_obj_set_style_bg_opa(obj, lib.LV_OPA_70, lib.LV_STATE_PRESSED)
            lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_SCROLLABLE)
            lib.lv_obj_add_flag(obj, lib.LV_OBJ_FLAG_PRESS_LOCK)
            lib.lv_obj_remove_flag(obj, lib.LV_OBJ_FLAG_CLICK_FOCUSABLE)
            native = _Native(self, obj, (lib.LV_EVENT_PRESSED, lib.LV_EVENT_PRESSING))
            native.node = self
            handles.append(native)
        if store.get('fractions') is None or len(store['fractions']) != len(panes):
            store['fractions'] = [1 / len(panes)] * len(panes) if panes else []
        for i, pane in enumerate(panes):
            lib.lv_obj_move_to_index(pane.outer, 2 * i)
            pane._native.box_dims.update(('w', 'h'))
            if i < len(handles):
                lib.lv_obj_move_to_index(handles[i].obj, 2 * i + 1)
        self._arrange()
        super().postSync()

    def _arrange(self):
        obj = self.ui
        store = self._native.store
        panes = self._panes()
        handles = store.get('handles', [])
        lib.lv_obj_update_layout(obj)
        width = max(0, lib.lv_obj_get_content_width(obj))
        height = max(0, lib.lv_obj_get_content_height(obj))
        axis = height if self.vertical else width
        count = len(panes)
        gap = min(_HANDLE, axis // max(1, 2 * count - 1)) if count > 1 else 0
        usable = max(0, axis - gap * max(0, count - 1))
        fractions = store['fractions']
        position = 0
        for i, pane in enumerate(panes):
            extent = usable - position + i * gap if i == count - 1 else round(fractions[i] * usable)
            if self.vertical:
                lib.lv_obj_set_pos(pane.outer, 0, position)
                lib.lv_obj_set_size(pane.outer, width, extent)
            else:
                lib.lv_obj_set_pos(pane.outer, position, 0)
                lib.lv_obj_set_size(pane.outer, extent, height)
            position += extent
            if i < len(handles) and handles[i].obj is not None:
                h = handles[i].obj
                lib.lv_obj_set_pos(h, 0 if self.vertical else position, position if self.vertical else 0)
                lib.lv_obj_set_size(h, width if self.vertical else gap, gap if self.vertical else height)
                position += gap
            hook = getattr(pane, '_relayout', None)
            if hook is not None:
                hook()
        store['usable'] = usable

    def _lv_event(self, code, e):
        store = self._native.store
        if code == lib.LV_EVENT_SIZE_CHANGED and lib.lv_event_get_target_obj(e) == self.ui:
            runtime.post(lambda: self.get_node().ui is not None and self.get_node()._arrange())
        elif code in (lib.LV_EVENT_PRESSED, lib.LV_EVENT_PRESSING):
            target = lib.lv_event_get_target_obj(e)
            handles = [n.obj for n in store.get('handles', [])]
            if target not in handles:
                return
            index = handles.index(target)
            indev = lib.lv_indev_active()
            if indev == ffi.NULL:
                return
            point = ffi.new('lv_point_t *')
            lib.lv_indev_get_point(indev, point)
            coordinate = point.y if self.vertical else point.x
            fractions = store['fractions']
            if code == lib.LV_EVENT_PRESSED:
                store['drag'] = (coordinate, fractions[index], fractions[index + 1])
            elif store.get('drag') and store.get('usable'):
                start, first, second = store['drag']
                total = first + second
                moved = first + (coordinate - start) / store['usable']
                fractions[index] = max(0.0, min(total, moved))
                fractions[index + 1] = total - fractions[index]
                self._arrange()
        else:
            super()._lv_event(code, e)
