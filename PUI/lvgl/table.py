from __future__ import annotations
from .. import _typing as _t
from .._table import CellEdit, TableData, TableNode, text
from .base import *
from .overlay import create_dialog, Handlers


def _text_width(obj, value):
    point = ffi.new('lv_point_t *')
    lib.lv_text_get_size(point, ffi.new('char[]', value.encode('utf-8')),
                         lib.lv_obj_get_style_text_font(obj, lib.LV_PART_ITEMS),
                         0, 0, lib.LV_COORD_MAX, 0)
    return point.x


class Table(TableData, LBaseWidget):
    """lv_table; headers occupy the first row/column. Double click (or Enter)
    edits a cell in a dialog."""
    expand_x_prio = expand_y_prio = 4
    pui_terminal = False
    _always_clickable = True
    _lv_events = (lib.LV_EVENT_VALUE_CHANGED,)

    def __init__(self, model: _t.Any = None, autofit: bool = True, columnHeader: _t.Sequence[_t.Any] | None = None,
                 rowHeader: _t.Sequence[_t.Any] | None = None, columnCount: int | None = None,
                 rowCount: int | None = None) -> None:
        super().__init__()
        self._init_table(model, autofit, columnHeader, rowHeader, columnCount, rowCount)

    def create(self, parent):
        obj = lib.lv_table_create(parent)
        # Compact desktop-like cells (the theme default is touch sized).
        lib.lv_obj_set_style_pad_top(obj, 4, lib.LV_PART_ITEMS)
        lib.lv_obj_set_style_pad_bottom(obj, 4, lib.LV_PART_ITEMS)
        lib.lv_obj_set_style_pad_left(obj, 8, lib.LV_PART_ITEMS)
        lib.lv_obj_set_style_pad_right(obj, 8, lib.LV_PART_ITEMS)
        return obj

    def adopt(self, prev):
        self.editor = prev.editor

    def _offsets(self):
        return (1 if self._has_header('columnHeader') else 0,
                1 if self._has_header('rowHeader') else 0)

    def postSync(self):
        if self.ui is None:
            return super().postSync()
        obj = self.ui
        rows, cols = self._dimensions()
        top, left = self._offsets()
        store = self._native.store
        lib.lv_table_set_row_count(obj, rows + top)
        lib.lv_table_set_column_count(obj, cols + left)
        values = {}
        if top:
            for c in range(cols):
                values[(0, c + left)] = self._header('columnHeader', c)
        if left:
            for r in range(rows):
                values[(r + top, 0)] = self._header('rowHeader', r)
            if top:
                values[(0, 0)] = ''
        for r in range(rows):
            for c in range(cols):
                values[(r + top, c + left)] = self._display(self._cell(r, c))
        previous = store.get('values', {})
        for key, value in values.items():
            if previous.get(key) != value:
                lib.lv_table_set_cell_value(obj, key[0], key[1], text_bytes(value))
        store['values'] = values
        if self.autofit:
            pad = (lib.lv_obj_get_style_pad_left(obj, lib.LV_PART_ITEMS)
                   + lib.lv_obj_get_style_pad_right(obj, lib.LV_PART_ITEMS))
            for c in range(cols + left):
                width = max([_text_width(obj, values.get((r, c), '')) for r in range(rows + top)] + [20])
                lib.lv_table_set_column_width(obj, c, width + pad + 2)
        self._check_editor()
        super().postSync()

    def _selected(self):
        """The cell under the pointer. lv_table clears its selection on
        release, before CLICKED/DOUBLE_CLICKED, so the cell reported by
        VALUE_CHANGED (sent during release) is remembered instead."""
        row = ffi.new('uint32_t *')
        col = ffi.new('uint32_t *')
        lib.lv_table_get_selected_cell(self.ui, row, col)
        if row[0] == lib.LV_TABLE_CELL_NONE or col[0] == lib.LV_TABLE_CELL_NONE:
            return self._native.store.get('cell')
        return row[0], col[0]

    def _lv_event(self, code, e):
        if code == lib.LV_EVENT_VALUE_CHANGED:
            row = ffi.new('uint32_t *')
            col = ffi.new('uint32_t *')
            lib.lv_table_get_selected_cell(self.ui, row, col)
            if row[0] != lib.LV_TABLE_CELL_NONE and col[0] != lib.LV_TABLE_CELL_NONE:
                self._native.store['cell'] = (row[0], col[0])
        elif code in (lib.LV_EVENT_CLICKED, lib.LV_EVENT_DOUBLE_CLICKED):
            cell = self._selected()
            if cell is None:
                return
            top, left = self._offsets()
            info = self._cell(cell[0] - top, cell[1] - left)
            if info is None:
                return  # a header cell
            double = code == lib.LV_EVENT_DOUBLE_CLICKED
            target = self._target(info)
            self._preClicked()
            runtime.post(lambda: self._activate(target, double))

    def _activate(self, target, double):
        node = self.get_node()
        if node.destroyed:
            return
        info = node._locate(target)
        if info is None:
            return
        node._dispatch(info, double)
        if double:
            node = node.get_node()
            node._edit(node._locate(target))

    def _open_editor(self, target, value):
        self.editor = _CellEditor(self, target, value)

    def destroy(self, direct):
        if self.editor is not None:
            self.editor.close()
        super().destroy(direct)


class _CellEditor(CellEdit):
    def __init__(self, table, target, value):
        super().__init__(table, target, value)
        self.handlers = Handlers()
        self.backdrop, panel, body, close = create_dialog('Edit cell', on_close=True)
        self.handlers.on(close, lib.LV_EVENT_CLICKED, lambda code, e: self.close())
        row = lib.lv_obj_create(body)
        lib.lv_obj_remove_style_all(row)
        lib.lv_obj_set_size(row, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
        lib.lv_obj_set_flex_flow(row, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(row, lib.LV_FLEX_ALIGN_START, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        lib.lv_obj_set_style_pad_column(row, 6, SEL)
        prefix, suffix = self.decorations
        if prefix:
            lib.lv_label_set_text(lib.lv_label_create(row), text_bytes(prefix))
        self.kind = None
        if self.choices is not None:
            self.kind = 'choice'
            self.field = lib.lv_dropdown_create(row)
            lib.lv_dropdown_set_options(self.field, '\n'.join(label.replace('\n', ' ') for _, label in self.choices).encode())
            index = next((i for i, (item, _) in enumerate(self.choices) if item == value), -1)
            if index >= 0:
                lib.lv_dropdown_set_selected(self.field, index)
            else:
                lib.lv_dropdown_set_text(self.field, text_bytes(text(value)))
            self.index = index
            self.handlers.on(self.field, lib.LV_EVENT_VALUE_CHANGED, self._chosen)
        elif type(value) is bool:
            self.kind = 'bool'
            self.field = lib.lv_checkbox_create(row)
            lib.lv_checkbox_set_text(self.field, b'' if any(self.decorations) else b'Value')
            lib.lv_obj_set_state(self.field, lib.LV_STATE_CHECKED, value)
        else:
            self.field = lib.lv_textarea_create(row)
            lib.lv_textarea_set_one_line(self.field, True)
            lib.lv_obj_set_width(self.field, 260)
            lib.lv_textarea_set_text(self.field, text_bytes(text(value)))
            if self.placeholder:
                lib.lv_textarea_set_placeholder_text(self.field, text_bytes(self.placeholder))
            self.handlers.on(self.field, lib.LV_EVENT_READY, lambda code, e: self.save())
            lib.lv_obj_set_state(self.field, lib.LV_STATE_FOCUSED, True)
            lib.lv_group_focus_obj(self.field)
        if suffix:
            lib.lv_label_set_text(lib.lv_label_create(row), text_bytes(suffix))
        self.error = lib.lv_label_create(body)
        lib.lv_obj_set_style_text_color(self.error, lib.lv_color_hex(0xD32F2F), SEL)
        lib.lv_label_set_text(self.error, b'')
        buttons = lib.lv_obj_create(body)
        lib.lv_obj_remove_style_all(buttons)
        lib.lv_obj_set_size(buttons, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
        lib.lv_obj_set_style_min_width(buttons, lib.lv_pct(100), SEL)
        lib.lv_obj_set_flex_flow(buttons, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(buttons, lib.LV_FLEX_ALIGN_END, lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        lib.lv_obj_set_style_pad_column(buttons, 8, SEL)
        for caption, action in (('Cancel', self.close), ('Save', self.save)):
            button = lib.lv_button_create(buttons)
            lib.lv_label_set_text(lib.lv_label_create(button), caption.encode())
            self.handlers.on(button, lib.LV_EVENT_CLICKED, lambda code, e, action=action: action())

    def _chosen(self, code, e):
        self.index = lib.lv_dropdown_get_selected(self.field)

    def show_error(self, message):
        lib.lv_label_set_text(self.error, text_bytes(message))

    def save(self):
        if self.closed:
            return
        if self.kind == 'choice':
            value = self.index
        elif self.kind == 'bool':
            value = bool(lib.lv_obj_has_state(self.field, lib.LV_STATE_CHECKED))
        else:
            raw = lib.lv_textarea_get_text(self.field)
            value = ffi.string(raw).decode('utf-8', 'replace') if raw != ffi.NULL else ''
        # Commit after this native callback returns: saving may close the dialog.
        runtime.post(lambda: self.save_value(value))

    def close(self):
        if self.closed:
            return
        self._detach()
        self.handlers.clear()
        backdrop, self.backdrop = self.backdrop, None
        if backdrop is not None:
            runtime.post(lambda: lib.lv_obj_delete(backdrop))
