from collections.abc import Mapping, Sequence

from .._table import decorate, decorations, placeholder
from .base import *


def _resolve(value):
    return value.value if isinstance(value, BaseBinding) else value


def _text(value):
    return '' if value is None else str(value)


def _choice_field(content):
    if isinstance(content, ft.Dropdown):
        return content
    if isinstance(content, ft.Row):
        return next((control for control in content.controls if isinstance(control, ft.Dropdown)), None)
    return None


class TableNode(PUINode):
    def __init__(self, data='', *, display=None, choices=None, prefix='', suffix='',
                 placeholder=None):
        super().__init__()
        if choices is not None and (
            isinstance(choices, (str, bytes))
            or not isinstance(choices, (Mapping, Sequence))
        ):
            raise TypeError('choices must be a mapping, sequence, or None')
        self.data, self.display, self.choices = data, display, choices
        self.prefix, self.suffix = prefix, suffix
        self.placeholder = placeholder
        self._set_callback = None

    def choiceItems(self):
        if isinstance(self.choices, Mapping):
            return self.choices.items()
        return ((value, value) for value in self.choices)

    def set(self, cb, *args, **kwargs):
        self._set_callback = (cb, args, kwargs)
        return self

    def _set(self, value):
        if self._set_callback:
            cb, args, kwargs = self._set_callback
            cb(value, *args, **kwargs)

    def update(self, prev):
        self.ui = prev.ui if prev else None
        super().update(prev)

    def releaseRetiredRefs(self):
        self._set_callback = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self._set_callback = None
        super().destroy(direct)


class Table(FBase):
    def __init__(self, model=None, autofit=True, columnHeader=None,
                 rowHeader=None, columnCount=None, rowCount=None):
        super().__init__()
        for name, count in (('columnCount', columnCount), ('rowCount', rowCount)):
            if count is not None and (
                not isinstance(count, int) or isinstance(count, bool) or count < 0
            ):
                raise ValueError(f'{name} must be a non-negative integer or None')
        if not autofit:
            raise NotImplementedError('Flet DataTable requires content-based column sizing (autofit=True)')
        self.layout_weight = 1
        self.model, self.autofit = model, autofit
        self.columnHeader, self.rowHeader = columnHeader, rowHeader
        self.columnCount, self.rowCount = columnCount, rowCount
        self.editor = None
        self.generation = object()

    def update(self, prev):
        if prev:
            self.ui, self.hscroll, self.vscroll = prev.ui, prev.hscroll, prev.vscroll
            self.editor = prev.editor
        else:
            # A zero-column table is kept out of the native tree in postSync.
            self.ui = ft.DataTable(columns=[ft.DataColumn(label='')], show_checkbox_column=False)
            self.hscroll = ft.Row(scroll=ft.ScrollMode.AUTO)
            self.vscroll = ft.Column(controls=[self.hscroll], scroll=ft.ScrollMode.AUTO, expand=True)
        super().update(prev)
        self.shell.content = self.vscroll

    def _dimensions(self):
        if self.model is not None:
            return self.model.rowCount(), self.model.columnCount()
        rows = self.rowCount if self.rowCount is not None else max(len(self.children), len(self.rowHeader or []))
        cols = self.columnCount if self.columnCount is not None else max(
            [len(self.columnHeader or [])] + [len(row.children) for row in self.children])
        return rows, cols

    def _has_header(self, name):
        return getattr(self, name) is not None or (
            self.model is not None and getattr(self.model, name) is not None)

    def _header(self, name, index):
        getter = getattr(self.model, name) if self.model is not None else None
        if getter is not None:
            return _text(getter(index))
        labels = getattr(self, name)
        return _text(labels[index]) if labels is not None and index < len(labels) else ''

    def _locate(self, target):
        if self.destroyed:
            return None
        rows, cols = self._dimensions()
        if isinstance(target, TableNode):
            cell = target.get_node()
            if self.model is not None or cell.destroyed or cell.parent is None:
                return None
            row = cell.parent.get_node()
            if row not in self.children or cell not in row.children:
                return None
            r, c = self.children.index(row), row.children.index(cell)
        else:
            generation, r, c = target
            if self.model is None or generation is not self.generation:
                return None
            cell = None
        return (r, c, cell) if r < rows and c < cols else None

    def _raw(self, info):
        r, c, cell = info
        return self.model.editData(r, c) if cell is None else _resolve(cell.data)

    def _display(self, info):
        r, c, cell = info
        if cell is None:
            return self.model.data(r, c)
        if cell.display is not None:
            value = _resolve(cell.display)
        else:
            value = _resolve(cell.data)
            if isinstance(cell.choices, Mapping):
                try:
                    value = _resolve(cell.choices.get(value, value))
                except TypeError:
                    pass
        return decorate(cell, value)

    def _decorations(self, info):
        return decorations(info[2])

    def _placeholder(self, info):
        return placeholder(info[2])

    def _editable(self, info):
        r, c, cell = info
        return self.model.editable(r, c) if cell is None else (
            isinstance(cell.data, BaseBinding) or cell._set_callback is not None)

    def _commit(self, info, value):
        root = self.root
        r, c, cell = info
        if cell is None:
            self.model.setData(r, c, value)
        elif isinstance(cell.data, BaseBinding):
            cell.data.value = value
        else:
            cell._set(value)
        root.redraw()

    def _tap(self, target, double=False):
        node = self.get_node()
        info = node._locate(target)
        if info is None:
            return
        node._preClicked()
        node = node.get_node()
        info = node._locate(target)
        if info is None:
            return
        r, c, cell = info
        if cell is None:
            (node.model.dblclicked if double else node.model.clicked)(r, c)
        else:
            (cell._dblclicked if double else cell._clicked)(None)
        # A callback can synchronously redraw or remove the table.
        node = node.get_node()
        info = node._locate(target)
        if info is None or not node._editable(info):
            return
        cell = info[2]
        if cell is not None and cell.choices is not None:
            return
        value = node._raw(info)
        if value is not None and type(value) not in (str, int, float, bool):
            return
        if node.editor is None:
            node.editor = _CellEditor(node, target, value)
            FView.application(node).ui.show_dialog(node.editor.dialog)

    def _render_cell(self, target, native, info):
        cell = info[2]
        editable = self._editable(info)
        value = self._raw(info) if editable else None
        choices = cell.choiceItems() if cell is not None and cell.choices is not None and editable else None
        if native is None:
            native = ft.DataCell(content='')

        async def tap(event):
            self.get_node()._tap(target)

        async def double_tap(event):
            self.get_node()._tap(target, double=True)

        native.on_tap, native.on_double_tap = tap, double_tap
        native.show_edit_icon = editable and choices is None and (
            value is None or type(value) in (str, int, float, bool))
        if choices is not None:
            # DataCell gestures intercept the embedded Dropdown's menu button.
            native.on_tap = native.on_double_tap = None
            items = [(_resolve(value), _text(_resolve(label))) for value, label in choices]
            dropdown = _choice_field(native.content) or ft.Dropdown(dense=True)
            dropdown.options = [ft.DropdownOption(key=str(i), text=label) for i, (_, label) in enumerate(items)]
            dropdown.value = next((str(i) for i, (item, _) in enumerate(items) if item == value), None)
            dropdown.hint_text = self._placeholder(info) or _text(value)
            dropdown.label = _text(_resolve(cell.display)) if cell.display is not None else None
            dropdown.text_style = self.ui.data_text_style

            async def select(event):
                node = self.get_node()
                current = node._locate(target)
                if (current is None or not node._editable(current)
                        or _choice_field(current[2].ui.content) is not dropdown):
                    return
                try:
                    index = int(dropdown.value)
                except (TypeError, ValueError):
                    return
                if 0 <= index < len(items):
                    node._preClicked()
                    node = node.get_node()
                    current = node._locate(target)
                    if current is not None and node._editable(current):
                        node._commit(current, items[index][0])

            dropdown.on_select = select
            parts = self._decorations(info)
            if any(parts):
                controls = [ft.Text(parts[0])] if parts[0] else []
                controls.append(dropdown)
                if parts[1]:
                    controls.append(ft.Text(parts[1]))
                native.content = ft.Row(controls=controls, spacing=0, tight=True)
            else:
                native.content = dropdown
        else:
            native.content = _text(self._display(info))
        return native

    def postSync(self):
        rows, cols = self._dimensions()
        headers = self._has_header('rowHeader')
        self.ui.columns = [ft.DataColumn(label='')] if headers else []
        self.ui.columns += [ft.DataColumn(label=self._header('columnHeader', c)) for c in range(cols)]
        self.ui.heading_row_height = None if self._has_header('columnHeader') else 0
        native_rows = []
        for r in range(rows):
            row = self.children[r] if self.model is None and r < len(self.children) else None
            cells = [ft.DataCell(content=self._header('rowHeader', r))] if headers else []
            for c in range(cols):
                if self.model is not None:
                    cells.append(self._render_cell((self.generation, r, c), None, (r, c, None)))
                elif row is not None and c < len(row.children):
                    cell = row.children[c]
                    cell.ui = self._render_cell(cell, cell.ui, (r, c, cell))
                    cells.append(cell.ui)
                else:
                    cells.append(ft.DataCell(content=''))
            native = row.ui if row is not None and row.ui is not None else ft.DataRow(cells=[])
            native.cells = cells
            if row is not None:
                row.ui = native
            native_rows.append(native)
        self.ui.rows = native_rows
        self.hscroll.controls = [self.ui] if self.ui.columns else []
        if self.editor is not None and not self.editor.valid():
            self.editor.close()

    def releaseRetiredRefs(self):
        self.editor = None
        self.hscroll = self.vscroll = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        if self.editor is not None:
            self.editor.close()
        self.hscroll = self.vscroll = None
        super().destroy(direct)


class _CellEditor:
    def __init__(self, table, target, value):
        self.table, self.target, self.original = table, target, value
        self.decorations = table._decorations(table._locate(target))
        self.placeholder = table._placeholder(table._locate(target))
        decorated = any(self.decorations)
        self.field = ft.Checkbox(label='' if decorated else 'Value', value=value) if type(value) is bool else ft.TextField(
            label=None if decorated else 'Value', value=_text(value), hint_text=self.placeholder,
            autofocus=True, on_submit=self.save)
        content = self.field
        if decorated:
            controls = [ft.Text(self.decorations[0])] if self.decorations[0] else []
            controls.append(self.field)
            if self.decorations[1]:
                controls.append(ft.Text(self.decorations[1]))
            content = ft.Row(controls=controls, spacing=0, tight=True)
        self.error = ft.Text(color=ft.Colors.ERROR, visible=False)
        self.dialog = ft.AlertDialog(
            modal=True, title=ft.Text('Edit cell'),
            content=ft.Column(controls=[content, self.error], tight=True),
            actions=[ft.TextButton('Cancel', on_click=self.cancel), ft.TextButton('Save', on_click=self.save)],
            on_dismiss=self.dismissed)

    def valid(self):
        table = self.table.get_node()
        info = table._locate(self.target)
        if info is None or not table._editable(info):
            return False
        cell = info[2]
        if cell is not None and cell.choices is not None:
            return False
        value = table._raw(info)
        return (type(value) is type(self.original)
                and (value is self.original or value == self.original)
                and self.decorations == table._decorations(info)
                and self.placeholder == table._placeholder(info))

    def close(self):
        table = self.table.get_node()
        was_open = self.dialog.open
        self.dialog.open = False
        if table.editor is self:
            table.editor = None
        if was_open:
            self.update()

    async def dismissed(self, event):
        # show_dialog has already removed the native dialog at this point.
        self.dialog.open = False
        self.close()

    async def cancel(self, event):
        self.close()

    def update(self):
        app = FView.application(self.table.get_node())
        if app is not None and app.ready:
            app.ui.update(self.dialog)

    def show_error(self, message):
        if isinstance(self.field, ft.TextField):
            self.field.error = message
        else:
            self.error.value, self.error.visible = message, True
        self.update()

    async def save(self, event):
        table = self.table.get_node()
        if table.editor is not self or not self.valid():
            self.close()
            return
        try:
            value = self.field.value
            if type(self.original) in (int, float):
                value = type(self.original)(value)
        except (TypeError, ValueError):
            self.show_error('Enter a whole number.' if type(self.original) is int else 'Enter a number.')
            return
        try:
            table._commit(table._locate(self.target), value)
        except (TypeError, ValueError) as error:
            self.show_error(str(error))
            return
        self.close()
