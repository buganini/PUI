from __future__ import annotations
from .. import _typing as _t
from ..common import combobox_get, combobox_record_selection, combobox_set_text
from .base import *
from .overlay import Handlers

_SYMBOL_DOWN = b"\xef\x81\xb8"


class ComboBox(LBaseWidget):
    """Drop-down list of ComboBoxItem children.

    Non-editable: a native lv_dropdown. Editable: a text field with a button
    and a candidate list on the top layer; typed text is committed on Enter,
    focus loss or by picking a candidate (edit_model follows every keystroke).
    """
    pui_terminal = False
    _always_clickable = True
    _lv_events = (lib.LV_EVENT_VALUE_CHANGED,)

    def __init__(self, editable: bool = False, *, index_model: _t.Binding[_t.Any] | None = None,
                 text_model: _t.Binding[_t.Any] | None = None, edit_model: _t.Binding[_t.Any] | None = None,
                 disabled: bool = False, autoexpand: bool = True) -> None:
        super().__init__()
        self.editable = editable
        self.index_model = index_model
        self.text_model = text_model
        self.edit_model = edit_model
        self.disabled = disabled
        self.autoexpand = autoexpand
        self.combo_state = {'key': None, 'text': ''}

    def adopt(self, prev):
        self.combo_state = prev.combo_state

    def create(self, parent):
        if not self.editable:
            return lib.lv_dropdown_create(parent)
        box = lib.lv_obj_create(parent)
        lib.lv_obj_remove_style_all(box)
        lib.lv_obj_set_flex_flow(box, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(box, lib.LV_FLEX_ALIGN_START, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        lib.lv_obj_set_style_pad_column(box, 4, SEL)
        field = lib.lv_textarea_create(box)
        lib.lv_textarea_set_one_line(field, True)
        lib.lv_obj_set_width(field, 220)
        button = lib.lv_button_create(box)
        lib.lv_obj_set_style_pad_all(button, 8, SEL)
        lib.lv_label_set_text(lib.lv_label_create(button), _SYMBOL_DOWN)
        self._parts = (field, button)
        return box

    def update(self, prev):
        if prev is not None and prev.ui is not None and prev.editable != self.editable:
            # The native control differs; replace it at the same position.
            index = lib.lv_obj_get_index(prev.ui)
            native = prev._native
            native.node = None
            lib.lv_obj_delete(prev.ui)
            prev.ui = None
            super().update(None)
            lib.lv_obj_move_to_index(self.ui, index)
            return
        super().update(prev)

    def _default_dims(self):
        return ('content', 'content') if self.editable else (None, None)

    def _apply_dim(self, horizontal):
        self._default_size = self._default_dims()
        super()._apply_dim(horizontal)

    def configure(self, prev):
        store = self._native.store
        if self.editable and 'field' not in store:
            field, button = self._parts
            store['field'], store['button'] = field, button
            handlers = store['handlers'] = Handlers()
            store['on_delete'] = [lambda: _popup.close(store), handlers.clear]
            handlers.on(field, lib.LV_EVENT_VALUE_CHANGED, lambda c, e: self.get_node()._typed())
            handlers.on(field, lib.LV_EVENT_READY, lambda c, e: runtime.post(self.get_node()._commit))
            handlers.on(field, lib.LV_EVENT_DEFOCUSED, lambda c, e: runtime.post(self.get_node()._commit))
            handlers.on(button, lib.LV_EVENT_CLICKED, lambda c, e: runtime.post(self.get_node()._toggle_popup))
        if self.editable:
            for part in (store['field'], store['button']):
                lib.lv_obj_set_state(part, lib.LV_STATE_DISABLED, bool(self.disabled))
        else:
            lib.lv_obj_set_state(self.ui, lib.LV_STATE_DISABLED, bool(self.disabled))

    def _items(self):
        return [c for c in self.children if isinstance(c, ComboBoxItem)]

    def postSync(self):
        if self.ui is None:
            return
        store = self._native.store
        items = self._items()
        index, text = combobox_get(items, self.index_model, self.text_model, self.editable, self.combo_state)
        store['syncing'] = True
        try:
            if self.editable:
                if not store.get('editing'):
                    field = store['field']
                    raw = lib.lv_textarea_get_text(field)
                    if (ffi.string(raw).decode('utf-8', 'replace') if raw != ffi.NULL else '') != str(text):
                        lib.lv_textarea_set_text(field, text_bytes(text))
                if _popup.owner is store:
                    _popup.fill(self)
            else:
                options = '\n'.join(str(c.text).replace('\n', ' ') for c in items)
                if store.get('options') != options:
                    lib.lv_dropdown_set_options(self.ui, options.encode('utf-8'))
                    store['options'] = options
                if index is not None and 0 <= index < len(items):
                    lib.lv_dropdown_set_selected(self.ui, index)
                    lib.lv_dropdown_set_text(self.ui, ffi.NULL)
                else:
                    # No selection (or free text): show the text instead of item 0.
                    lib.lv_dropdown_set_text(self.ui, text_bytes(text or ''))
        finally:
            store['syncing'] = False
        super().postSync()

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_VALUE_CHANGED and not self.editable:
            if self._native.store.get('syncing'):
                return
            self._choose(lib.lv_dropdown_get_selected(self.ui))
        else:
            super()._lv_event(code, e)

    def _choose(self, idx):
        node = self.get_node()
        items = node._items()
        if node.index_model is not None:
            node.index_model.value = idx
        if node.text_model is not None:
            node.text_model.value = items[idx].value if 0 <= idx < len(items) else ''
        combobox_record_selection(items, idx, node.combo_state)
        if node.editable and node.ui is not None:
            store = node._native.store
            store['editing'] = False
            if 0 <= idx < len(items):
                store['syncing'] = True
                lib.lv_textarea_set_text(store['field'], text_bytes(items[idx].text))
                store['syncing'] = False
            if node.edit_model is not None and 0 <= idx < len(items):
                node.edit_model.value = str(items[idx].text)
        ev = PUIEvent()
        ev.value = idx
        node._change(ev)

    # ---- editable ----
    def _field_text(self):
        raw = lib.lv_textarea_get_text(self._native.store['field'])
        return ffi.string(raw).decode('utf-8', 'replace') if raw != ffi.NULL else ''

    def _typed(self):
        store = self._native.store
        if store.get('syncing'):
            return
        store['editing'] = True
        text = self._field_text()
        if self.edit_model is not None:
            self.edit_model.value = text
        ev = PUIEvent()
        ev.value = text
        self._input(ev)
        if self.autoexpand and not self.disabled:
            runtime.post(lambda: self.get_node()._open_popup())

    def _commit(self):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        store = node._native.store
        if not store.get('editing'):
            return
        store['editing'] = False
        text = node._field_text()
        items = node._items()
        match = next((i for i, item in enumerate(items) if str(item.text) == text), -1)
        if match >= 0:
            node._choose(match)
            return
        combobox_set_text(node.index_model, node.text_model, text, node.combo_state)
        ev = PUIEvent()
        ev.value = text
        node._change(ev)

    def _open_popup(self):
        node = self.get_node()
        if not node.destroyed and node.ui is not None and node.editable:
            _popup.open(node)

    def _toggle_popup(self):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        if _popup.owner is node._native.store:
            _popup.close()
        else:
            _popup.open(node)

    def destroy(self, direct):
        if self._native is not None:
            _popup.close(self._native.store)
        super().destroy(direct)


class _CandidatePopup:
    """Candidate list for the editable ComboBox that has the focus."""

    def __init__(self):
        self.owner = None
        self.panel = None
        self.handlers = Handlers()

    def close(self, owner=None):
        if owner is not None and owner is not self.owner:
            return
        self.handlers.clear()
        if self.panel is not None:
            lib.lv_obj_delete(self.panel)
        self.panel = None
        self.owner = None

    def _forget(self):
        # LVGL deleted the panel (its display went away).
        self.panel = None
        self.owner = None

    def open(self, node):
        store = node._native.store
        if self.owner is not store:
            self.close()
            self.owner = store
            panel = self.panel = lib.lv_obj_create(lib.lv_layer_top())
            lib.lv_obj_set_flex_flow(panel, lib.LV_FLEX_FLOW_COLUMN)
            lib.lv_obj_set_style_pad_all(panel, 2, SEL)
            lib.lv_obj_set_style_pad_row(panel, 0, SEL)
            lib.lv_obj_set_style_radius(panel, 4, SEL)
            lib.lv_obj_set_scroll_dir(panel, lib.LV_DIR_VER)
            lib.lv_obj_set_style_max_height(panel, 240, SEL)
            self.handlers.on_delete(panel, self._forget)
        self.fill(node)

    def fill(self, node):
        store = node._native.store
        panel = self.panel
        self.handlers.clear()
        lib.lv_obj_clean(panel)
        items = node._items()
        if not items:
            self.close()
            return
        field = store['field']
        lib.lv_obj_update_layout(field)
        lib.lv_obj_set_width(panel, lib.lv_obj_get_width(node.ui))
        lib.lv_obj_set_height(panel, lib.LV_SIZE_CONTENT)
        for index, item in enumerate(items):
            row = lib.lv_obj_create(panel)
            lib.lv_obj_remove_style_all(row)
            lib.lv_obj_set_size(row, lib.lv_pct(100), lib.LV_SIZE_CONTENT)
            lib.lv_obj_set_style_pad_all(row, 6, SEL)
            lib.lv_obj_set_style_bg_color(row, lib.lv_color_hex(0x2196F3), lib.LV_STATE_PRESSED)
            lib.lv_obj_set_style_bg_opa(row, lib.LV_OPA_COVER, lib.LV_STATE_PRESSED)
            lib.lv_obj_add_flag(row, lib.LV_OBJ_FLAG_CLICKABLE)
            lib.lv_label_set_text(lib.lv_label_create(row), text_bytes(item.text))
            self.handlers.on(row, lib.LV_EVENT_CLICKED,
                             lambda c, e, index=index, node=node: runtime.post(lambda: self._pick(node, index)))
        lib.lv_obj_align_to(panel, node.ui, lib.LV_ALIGN_OUT_BOTTOM_LEFT, 0, 2)

    def _pick(self, node, index):
        node = node.get_node()
        self.close()
        if not node.destroyed and node.ui is not None:
            node._choose(index)


_popup = _CandidatePopup()


class ComboBoxItem(PUINode):
    pui_terminal = True

    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
        super().__init__()
        self.id(text)
        self.text = text
        self.value = text if value is None else value


from ..fontcombobox import FontComboBoxMixin


class FontComboBox(FontComboBoxMixin, ComboBox):
    """LVGL renders only its built-in Montserrat bitmap fonts."""
    @staticmethod
    def default_fonts():
        return ('Montserrat',)

    def font_item(self, name):
        ComboBoxItem(name)
