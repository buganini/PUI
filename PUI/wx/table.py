"""Table declarations backed by wx's grid model and native in-cell controls."""
from __future__ import annotations
from .. import _typing as _t
from collections.abc import Mapping, Sequence

import wx.grid as gridlib
from .._table import decorate, decorations, placeholder
from .base import *


def _resolve(value):
    return value.value if isinstance(value, BaseBinding) else value


def _text(value):
    return '' if value is None else str(value)


class TableNode(PUINode):
    def __init__(self, data: _t.Any = '', *, display: _t.Any = None, choices: _t.Choices | None = None, prefix: _t.Any = '', suffix: _t.Any = '',
                 placeholder: _t.Any = None) -> None:
        super().__init__()
        if choices is not None and (isinstance(choices, (str, bytes))
                                    or not isinstance(choices, (Mapping, Sequence))):
            raise TypeError('choices must be a mapping, sequence, or None')
        self.data, self.display, self.choices = data, display, choices
        self.prefix, self.suffix = prefix, suffix
        self.placeholder = placeholder
        self._set_callback = None

    def choiceItems(self):
        return self.choices.items() if isinstance(self.choices, Mapping) else (
            (value, value) for value in self.choices)

    def set(self, cb, *args, **kwargs):
        self._set_callback = cb, args, kwargs
        return self

    def _set(self, value):
        if self._set_callback:
            cb, args, kwargs = self._set_callback
            cb(value, *args, **kwargs)


class _GridModel(gridlib.GridTableBase):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.rows = self.cols = 0
        self.generation = object()

    def GetNumberRows(self):
        return self.rows

    def GetNumberCols(self):
        return self.cols

    def cell(self, row, col):
        node = self.node
        if node is None or node.destroyed or not (0 <= row < self.rows and 0 <= col < self.cols):
            return None
        if node.model is not None:
            if row < node.model.rowCount() and col < node.model.columnCount():
                return row, col, None
        elif row < len(node.children) and col < len(node.children[row].children):
            return row, col, node.children[row].children[col]
        return None

    def raw(self, cell):
        row, col, child = cell
        return self.node.model.editData(row, col) if child is None else _resolve(child.data)

    def choices(self, cell):
        child = cell[2]
        if child is not None and child.choices is not None:
            return [(_resolve(value), _text(_resolve(label))) for value, label in child.choiceItems()]
        if type(self.raw(cell)) is bool:
            return [(False, 'False'), (True, 'True')]
        return None

    def decorations(self, cell):
        return decorations(cell[2])

    def placeholder(self, cell):
        return placeholder(cell[2])

    def editable(self, cell):
        if cell is None:
            return False
        row, col, child = cell
        enabled = self.node.model.editable(row, col) if child is None else (
            isinstance(child.data, BaseBinding) or child._set_callback is not None)
        return bool(enabled and (self.choices(cell) is not None
                                 or self.raw(cell) is None
                                 or type(self.raw(cell)) in (str, int, float)))

    def GetValue(self, row, col):
        cell = self.cell(row, col)
        if cell is None:
            return ''
        child = cell[2]
        if child is None:
            return _text(self.node.model.data(row, col))
        if child.display is not None:
            value = _resolve(child.display)
        else:
            value = _resolve(child.data)
            if isinstance(child.choices, Mapping):
                try:
                    value = _resolve(child.choices.get(value, value))
                except TypeError:
                    pass
        return decorate(child, value)

    def SetValue(self, row, col, value):
        cell = self.cell(row, col)
        if not self.editable(cell):
            return
        raw = self.raw(cell)
        try:
            if type(raw) is bool and isinstance(value, str):
                if value.lower() not in ('true', 'false', '1', '0'):
                    return
                converted = value.lower() in ('true', '1')
            else:
                converted = value if raw is None else type(raw)(value)
        except (ValueError, TypeError):
            return
        self.commit(cell, converted)

    def commit(self, cell, value):
        row, col, child = cell
        root = self.node.root
        if child is None:
            self.node.model.setData(row, col, value)
        elif isinstance(child.data, BaseBinding):
            child.data.value = value
        else:
            child._set(value)
        root.redraw()

    def IsEmptyCell(self, row, col):
        return self.GetValue(row, col) == ''

    def header(self, name, index):
        node = self.node
        if node is None:
            return ''
        getter = getattr(node.model, name, None) if node.model is not None else None
        if getter is not None:
            return _text(getter(index))
        labels = getattr(node, name)
        return _text(labels[index]) if labels is not None and index < len(labels) else ''

    def GetColLabelValue(self, col):
        return self.header('columnHeader', col)

    def GetRowLabelValue(self, row):
        return self.header('rowHeader', row)


class _CellEditor(gridlib.GridCellEditor):
    def __init__(self, choice=False, parts=('', ''), hint=''):
        super().__init__()
        self.choice = choice
        self.parts = parts
        self.hint = hint
        self.model = None
        self.pending = None

    def Clone(self):
        return _CellEditor(self.choice, self.parts, self.hint)

    def Create(self, parent, id, evtHandler):
        decorated = any(self.parts)
        control = wx.Control(parent, id) if decorated else None
        field_parent = control if decorated else parent
        self.field = wx.Choice(field_parent) if self.choice else wx.TextCtrl(
            field_parent, style=wx.TE_PROCESS_ENTER)
        if not self.choice:
            self.field.SetHint(self.hint)
        if decorated:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            if self.parts[0]:
                sizer.Add(wx.StaticText(control, label=self.parts[0]), 0, wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(self.field, 1, wx.EXPAND)
            if self.parts[1]:
                sizer.Add(wx.StaticText(control, label=self.parts[1]), 0, wx.ALIGN_CENTER_VERTICAL)
            control.SetSizer(sizer)
        else:
            control = self.field
        self.SetControl(control)
        if self.choice:
            self.field.Bind(wx.EVT_CHOICE, self.on_choice)
        if evtHandler is not None:
            control.PushEventHandler(evtHandler)
            if decorated:
                self.field.Bind(wx.EVT_KEY_DOWN, self.on_field_event)
                self.field.Bind(wx.EVT_KILL_FOCUS, self.on_field_event)

    def on_field_event(self, event):
        # The grid owns the handler on the registered outer control.
        if not self.GetControl().GetEventHandler().ProcessEvent(event):
            event.Skip()

    def on_choice(self, event):
        if self.valid():
            grid = self.model.GetView()
            grid.SaveEditControlValue()
            if grid:
                grid.DisableCellEditControl()

    def SetSize(self, rect):
        self.GetControl().SetSize(rect)

    def BeginEdit(self, row, col, grid):
        self.model = grid.GetTable()
        self.generation = self.model.generation
        self.cell = self.model.cell(row, col)
        self.original = self.model.raw(self.cell)
        self.pending = None
        control = self.field
        if self.choice:
            self.items = self.model.choices(self.cell)
            control.SetItems([label for _, label in self.items])
        self.Reset()
        control.SetFocus()
        if not self.choice:
            control.SelectAll()

    def valid(self):
        return (self.model is not None and self.model.node is not None
                and self.generation is self.model.generation
                and self.model.editable(self.model.cell(*self.cell[:2])))

    def EndEdit(self, row, col, grid, oldval):
        if not self.valid():
            return None
        control = self.field
        if self.choice:
            selected = control.GetSelection()
            if selected == wx.NOT_FOUND:
                return None
            value = self.items[selected][0]
        else:
            text = control.GetValue()
            if text == _text(self.original):
                return None
            try:
                value = text if self.original is None else type(self.original)(text)
            except (ValueError, TypeError):
                return None
        if type(value) is type(self.original) and value == self.original:
            return None
        self.pending = value
        return _text(value)

    def ApplyEdit(self, row, col, grid):
        if self.valid():
            value = self.pending
            self.original = value
            self.model.commit(self.model.cell(row, col), value)

    def Reset(self):
        control = self.field
        if self.choice:
            selected = next((i for i, (value, _) in enumerate(self.items)
                             if type(value) is type(self.original) and value == self.original), wx.NOT_FOUND)
            control.SetSelection(selected)
        else:
            control.ChangeValue(_text(self.original))

    def GetValue(self):
        return self.field.GetStringSelection() if self.choice else self.field.GetValue()

    def StartingKey(self, event):
        if not self.choice:
            key = event.GetUnicodeKey()
            if key != wx.WXK_NONE and key >= 32:
                self.field.ChangeValue(chr(key))
                self.field.SetInsertionPointEnd()
            elif event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_BACK):
                self.field.ChangeValue('')


class Table(WxBaseWidget):
    pui_terminal = False
    expand_x_prio = expand_y_prio = 3

    def __init__(self, model: _t.Any = None, autofit: bool = True, columnHeader: _t.Sequence[_t.Any] | None = None,
                 rowHeader: _t.Sequence[_t.Any] | None = None, columnCount: int | None = None, rowCount: int | None = None) -> None:
        super().__init__()
        for name, count in (('columnCount', columnCount), ('rowCount', rowCount)):
            if count is not None and (not isinstance(count, int) or isinstance(count, bool) or count < 0):
                raise ValueError(f'{name} must be a non-negative integer or None')
        self.layout_weight = 1
        self.model, self.autofit = model, autofit
        self.columnHeader, self.rowHeader = columnHeader, rowHeader
        self.columnCount, self.rowCount = columnCount, rowCount

    def update(self, prev):
        if prev and prev.ui:
            self.ui, self.grid_model = prev.ui, prev.grid_model
            # Match a model reset: never commit a draft into replaced/reordered data.
            self.grid_model.generation = object()
            self.ui.DisableCellEditControl()
        else:
            self.ui = gridlib.Grid(getWindow(self.parent))
            self.grid_model = _GridModel(self)
            self.ui.SetTable(self.grid_model, takeOwnership=True)
            self.header_sizes = self.ui.GetColLabelSize(), self.ui.GetRowLabelSize()
            self.ui.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self.on_click)
            self.ui.Bind(gridlib.EVT_GRID_CELL_LEFT_DCLICK, self.on_double_click)
        if prev:
            self.header_sizes = prev.header_sizes
        super().update(prev)

    def postSync(self):
        model, grid = self.grid_model, self.ui
        model.node = self
        if self.model is not None:
            rows, cols = self.model.rowCount(), self.model.columnCount()
        else:
            rows = self.rowCount if self.rowCount is not None else max(len(self.children), len(self.rowHeader or []))
            cols = self.columnCount if self.columnCount is not None else max(
                [len(self.columnHeader or [])] + [len(row.children) for row in self.children])
        grid.BeginBatch()
        try:
            for attr, count, added, deleted in (
                ('rows', rows, gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED, gridlib.GRIDTABLE_NOTIFY_ROWS_DELETED),
                ('cols', cols, gridlib.GRIDTABLE_NOTIFY_COLS_APPENDED, gridlib.GRIDTABLE_NOTIFY_COLS_DELETED),
            ):
                old = getattr(model, attr)
                setattr(model, attr, count)
                if count > old:
                    grid.ProcessTableMessage(gridlib.GridTableMessage(model, added, count - old))
                elif count < old:
                    grid.ProcessTableMessage(gridlib.GridTableMessage(model, deleted, count, old - count))
            for r in range(rows):
                for c in range(cols):
                    cell = model.cell(r, c)
                    editable = model.editable(cell)
                    grid.SetReadOnly(r, c, not editable)
                    if editable:
                        grid.SetCellEditor(
                            r, c, _CellEditor(model.choices(cell) is not None,
                                             model.decorations(cell), model.placeholder(cell)))
            for name, setter, size in (('columnHeader', grid.SetColLabelSize, self.header_sizes[0]),
                                       ('rowHeader', grid.SetRowLabelSize, self.header_sizes[1])):
                visible = getattr(self, name) is not None or (
                    self.model is not None and getattr(self.model, name, None) is not None)
                setter(size if visible else 0)
            grid.SetDefaultCellFont(grid.GetFont())
            grid.SetDefaultCellTextColour(grid.GetForegroundColour())
            grid.SetDefaultCellBackgroundColour(grid.GetBackgroundColour())
            if self.autofit and rows and cols:
                grid.AutoSizeColumns(False)
            grid.ForceRefresh()
        finally:
            grid.EndBatch()

    def dispatch(self, event, double=False):
        node = self.get_node()
        if node.destroyed:
            return
        row, col = event.GetRow(), event.GetCol()
        node._preClicked()
        node = node.get_node()
        cell = None if node.destroyed else node.grid_model.cell(row, col)
        if cell is not None:
            if cell[2] is None:
                (node.model.dblclicked if double else node.model.clicked)(row, col)
            else:
                (cell[2]._dblclicked if double else cell[2]._clicked)(None)
        if not node.get_node().destroyed:
            event.Skip()

    def on_click(self, event):
        self.dispatch(event)

    def on_double_click(self, event):
        self.dispatch(event, True)

    def destroy(self, direct):
        self.grid_model.generation = object()
        if self.ui:
            self.ui.DisableCellEditControl()
        self.grid_model.node = None
        super().destroy(direct)
