"""Single-column tree drawn as indented rows in a scrollable column."""
from __future__ import annotations
from .._tree import TreeData, TreeNode
from .base import *
from .overlay import Handlers

_SYMBOL_RIGHT = b'\xef\x81\x94'
_SYMBOL_DOWN = b'\xef\x81\xb8'
_INDENT = 18


class Tree(TreeData, LBaseWidget):
    _default_size = ('content', 'content')
    _always_clickable = True  # drag on blank space scrolls the rows

    def create(self, parent):
        obj = lib.lv_obj_create(parent)
        lib.lv_obj_set_flex_flow(obj, lib.LV_FLEX_FLOW_COLUMN)
        lib.lv_obj_set_style_pad_all(obj, 4, SEL)
        lib.lv_obj_set_style_pad_row(obj, 0, SEL)
        lib.lv_obj_set_style_radius(obj, 0, SEL)
        lib.lv_obj_set_scroll_dir(obj, lib.LV_DIR_ALL)
        return obj

    def configure(self, prev):
        store = self._native.store
        if 'rows' not in store:
            store['rows'] = []          # [(row, arrow, label)]
            store['handlers'] = Handlers()
            store['visible'] = []

            def cleanup(store=store):
                store['handlers'].clear()
            store['on_delete'] = [cleanup]

    def _row(self, index):
        store = self._native.store
        rows = store['rows']
        while len(rows) <= index:
            i = len(rows)
            row = lib.lv_obj_create(self.ui)
            lib.lv_obj_remove_style_all(row)
            lib.lv_obj_set_size(row, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
            lib.lv_obj_set_style_min_width(row, lib.lv_pct(100), SEL)
            lib.lv_obj_set_flex_flow(row, lib.LV_FLEX_FLOW_ROW)
            lib.lv_obj_set_flex_align(row, lib.LV_FLEX_ALIGN_START, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
            lib.lv_obj_set_style_pad_top(row, 3, SEL)
            lib.lv_obj_set_style_pad_bottom(row, 3, SEL)
            lib.lv_obj_set_style_pad_right(row, 6, SEL)
            lib.lv_obj_set_style_pad_column(row, 4, SEL)
            lib.lv_obj_set_style_bg_color(row, lib.lv_color_hex(0x2196F3), lib.LV_STATE_CHECKED)
            lib.lv_obj_set_style_bg_opa(row, lib.LV_OPA_COVER, lib.LV_STATE_CHECKED)
            lib.lv_obj_set_style_text_color(row, lib.lv_color_hex(0xFFFFFF), lib.LV_STATE_CHECKED)
            lib.lv_obj_add_flag(row, lib.LV_OBJ_FLAG_CLICKABLE)
            lib.lv_obj_remove_flag(row, lib.LV_OBJ_FLAG_SCROLLABLE)
            arrow = lib.lv_label_create(row)
            lib.lv_obj_set_width(arrow, 14)
            lib.lv_obj_add_flag(arrow, lib.LV_OBJ_FLAG_CLICKABLE)
            label = lib.lv_label_create(row)
            handlers = store['handlers']
            handlers.on(row, lib.LV_EVENT_CLICKED, lambda c, e, i=i: self._row_event(i, 'clicked'))
            handlers.on(row, lib.LV_EVENT_DOUBLE_CLICKED, lambda c, e, i=i: self._row_event(i, 'dblclicked'))
            handlers.on(arrow, lib.LV_EVENT_CLICKED, lambda c, e, i=i: self._row_event(i, 'toggle'))
            rows.append((row, arrow, label))
        return rows[index]

    def _render_tree(self):
        if self.ui is None:
            return
        state = self.tree_state
        store = self._native.store
        visible = state.visible()
        store['visible'] = [key for key, _ in visible]
        for index, (key, depth) in enumerate(visible):
            entry = state.entries[key]
            row, arrow, label = self._row(index)
            lib.lv_obj_remove_flag(row, lib.LV_OBJ_FLAG_HIDDEN)
            lib.lv_obj_set_style_pad_left(row, 4 + depth * _INDENT, SEL)
            symbol = (_SYMBOL_DOWN if key in state.expanded else _SYMBOL_RIGHT) if entry.children else b''
            lib.lv_label_set_text(arrow, symbol)
            lib.lv_label_set_text(label, text_bytes(entry.text))
            lib.lv_obj_set_state(row, lib.LV_STATE_CHECKED, key == state.selected)
        for row, _, _ in store['rows'][len(visible):]:
            lib.lv_obj_add_flag(row, lib.LV_OBJ_FLAG_HIDDEN)

    def _row_event(self, index, action):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        visible = node._native.store['visible']
        if index >= len(visible):
            return
        key = visible[index]
        state = node.tree_state
        if action == 'toggle':
            node.tree_event(key, 'collapsed' if key in state.expanded else 'expanded')
            return
        node.tree_event(key, action)
        if action == 'dblclicked':
            node = node.get_node()
            if not node.destroyed and key in node.tree_state.entries:
                node.tree_event(key, 'collapsed' if key in node.tree_state.expanded else 'expanded')
