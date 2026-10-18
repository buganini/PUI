from __future__ import annotations
from .. import _typing as _t
from rich.text import Text as RichText
from textual import containers, widgets
from textual.screen import ModalScreen

from .base import TBase
from .._table import CellEdit, TableData, TableNode, text


class _DataTable(widgets.DataTable):
    """Translate native cell activation without depending on hit-test internals."""
    _click_chain = 0

    def on_click(self, event):
        self._click_chain = event.chain

    def on_key(self, event):
        self._click_chain = 0

    def action_select_cursor(self):
        self._click_chain = 0
        super().action_select_cursor()

    def on_data_table_cell_selected(self, event):
        event.stop()
        node = self.puinode.get_node()
        chain, self._click_chain = self._click_chain, 0
        if node.destroyed:
            return
        row_key, col_key = event.cell_key
        # Resolve keys again: the native message may predate a redraw.
        if row_key.value not in node._rows or col_key.value not in node._columns:
            return
        info = node._cell(node._rows.index(row_key.value), node._columns.index(col_key.value))
        if info is None:
            return
        target = node._target(info)
        node._dispatch(info, double=chain == 2)
        node = node.get_node()
        if chain in (0, 2):
            node._edit(node._locate(target))


class Table(TableData, TBase):
    expand_x_prio = expand_y_prio = 3

    def __init__(self, model: _t.Any = None, autofit: bool = True, columnHeader: _t.Sequence[_t.Any] | None = None,
                 rowHeader: _t.Sequence[_t.Any] | None = None, columnCount: int | None = None, rowCount: int | None = None) -> None:
        super().__init__()
        self._init_table(model, autofit, columnHeader, rowHeader, columnCount, rowCount)

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui = prev.ui
            self.editor = prev.editor
            self._schema, self._rows, self._labels = prev._schema, prev._rows, prev._labels
        else:
            self.ui = _DataTable(cursor_type='cell')
            self._schema, self._rows, self._labels = None, [], []
        self.ui.puinode = self
        super().update(prev)

    def postSync(self):
        rows, cols = self._dimensions()
        keys = [self._row_key(r) for r in range(rows)]
        columns = [str(c) for c in range(cols)]
        headers = [self._header('columnHeader', c) for c in range(cols)]
        labels = [self._header('rowHeader', r) for r in range(rows)]
        values = [[RichText(self._display(self._cell(r, c))) for c in range(cols)] for r in range(rows)]
        schema = headers, self.autofit
        coordinate = self.ui.cursor_coordinate
        cursor_key = self._rows[coordinate.row] if coordinate.row < len(self._rows) else None
        scroll = self.ui.scroll_x, self.ui.scroll_y
        self.ui.show_header = self._has_header('columnHeader')
        self.ui.show_row_labels = self._has_header('rowHeader')
        reset_columns = schema != self._schema
        reset_rows = reset_columns or keys != self._rows or labels != self._labels
        if reset_rows:
            widths = {column.key.value: column.get_render_width(self.ui) - 2 * self.ui.cell_padding
                      for column in self.ui.ordered_columns}
            self.ui.clear(columns=reset_columns)
            if reset_columns:
                for c, key in enumerate(columns):
                    width = None if self.autofit else widths.get(key, max(
                        [RichText(headers[c]).cell_len] + [row[c].cell_len for row in values] + [1]))
                    self.ui.add_column(RichText(headers[c]), key=key, width=width)
            for r, key in enumerate(keys):
                self.ui.add_row(*values[r], key=key, label=RichText(labels[r]))
        else:
            for r, key in enumerate(keys):
                for c, column in enumerate(columns):
                    if self.ui.get_cell(key, column) != values[r][c]:
                        self.ui.update_cell(key, column, values[r][c], update_width=self.autofit)
        self._schema, self._rows, self._labels, self._columns = schema, keys, labels, columns
        if reset_rows:
            row = keys.index(cursor_key) if cursor_key in keys else min(coordinate.row, max(0, rows - 1))
            self.ui.move_cursor(row=row, column=min(coordinate.column, max(0, cols - 1)), scroll=False)
            self.ui.call_after_refresh(self._restore_scroll, self._generation, scroll)
        self._check_editor()

    def _restore_scroll(self, generation, scroll):
        node = self.get_node()
        if not node.destroyed and node._generation is generation:
            node.ui.scroll_to(x=scroll[0], y=scroll[1], animate=False, force=True, immediate=True)

    def _open_editor(self, target, value):
        self.editor = _CellEditor(self, target, value)
        self.ui.app.push_screen(self.editor)


class _CellEditor(CellEdit, ModalScreen):
    DEFAULT_CSS = """
    _CellEditor { align: center middle; }
    _CellEditor > Vertical {
        width: 60; max-width: 95%; height: auto; max-height: 95%;
        border: round $primary; padding: 1 2; background: $surface;
    }
    _CellEditor .table-actions { height: auto; align-horizontal: right; }
    _CellEditor .table-error { color: $error; height: auto; }
    _CellEditor .table-editor { height: auto; }
    _CellEditor .table-editor Input, _CellEditor .table-editor Select { width: 1fr; }
    _CellEditor .table-decoration { width: auto; height: auto; }
    """
    BINDINGS = [('escape', 'cancel', 'Cancel')]

    def __init__(self, table, target, value):
        ModalScreen.__init__(self)
        CellEdit.__init__(self, table, target, value)
        self._dismissed = False
        if self.choices is not None:
            index = next((i for i, (item, _) in enumerate(self.choices) if item == value), widgets.Select.NULL)
            self.field = widgets.Select([(RichText(label), i) for i, (_, label) in enumerate(self.choices)],
                                        value=index, allow_blank=True,
                                        prompt=self.placeholder or 'Choose a value')
        elif type(value) is bool:
            self.field = widgets.Checkbox('' if any(self.decorations) else 'Value', value=value)
        else:
            self.field = widgets.Input(value=text(value), placeholder=self.placeholder)
        self.error = widgets.Static('', classes='table-error', markup=False)

    def compose(self):
        with containers.Vertical():
            yield widgets.Label('Edit cell')
            if any(self.decorations):
                with containers.Horizontal(classes='table-editor'):
                    if self.decorations[0]:
                        yield widgets.Static(self.decorations[0], classes='table-decoration', markup=False)
                    yield self.field
                    if self.decorations[1]:
                        yield widgets.Static(self.decorations[1], classes='table-decoration', markup=False)
            else:
                yield self.field
            yield self.error
            with containers.Horizontal(classes='table-actions'):
                yield widgets.Button('Cancel', id='table-cancel')
                yield widgets.Button('Save', id='table-save', variant='primary')

    def on_mount(self):
        if self.closed:
            self._dismiss_if_active()
        else:
            self.field.focus()

    def on_screen_resume(self):
        if self.closed:
            self._dismiss_if_active()

    def on_unmount(self):
        self._detach()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == 'table-save':
            self.save()
        else:
            self.close()

    def on_input_changed(self, event):
        event.stop()  # The draft belongs to this screen, not PUI's TextField dispatcher.

    def on_checkbox_changed(self, event):
        event.stop()

    def on_input_submitted(self, event):
        event.stop()
        self.save()

    def action_cancel(self):
        self.close()

    def save(self):
        if not self.closed:
            self.save_value(self.field.value)

    def show_error(self, message):
        self.error.update(message)

    def close(self):
        if self.closed:
            return
        self._detach()
        self._dismiss_if_active()

    def _dismiss_if_active(self):
        if not self._dismissed and self.is_mounted and self.is_active:
            self._dismissed = True
            self.dismiss()
