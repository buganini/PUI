"""Data and draft handling for the native Tk and Textual tables."""
from __future__ import annotations
from . import _typing as _t
from collections.abc import Mapping, Sequence
from itertools import count

from .node import PUINode
from .state import AttrBinding, BaseBinding, DictBinding, ListBinding


_identities = count()


def resolve(value):
    return value.value if isinstance(value, BaseBinding) else value


def text(value):
    return '' if value is None else str(value)


def decorations(cell):
    if cell is None:
        return '', ''
    return tuple(text(resolve(getattr(cell, name, ''))) for name in ('prefix', 'suffix'))


def placeholder(cell):
    return '' if cell is None else text(resolve(getattr(cell, 'placeholder', None)))


def decorate(cell, value):
    prefix, suffix = decorations(cell)
    return prefix + text(value) + suffix


class TableNode(PUINode):
    def __init__(self, data: _t.Any = '', *, display: _t.Any = None, choices: _t.Choices | None = None, prefix: _t.Any = '', suffix: _t.Any = '',
                 placeholder: _t.Any = None) -> None:
        super().__init__()
        if choices is not None and (
            isinstance(choices, (str, bytes)) or not isinstance(choices, (Mapping, Sequence))
        ):
            raise TypeError('choices must be a mapping, sequence, or None')
        self.data, self.display, self.choices = data, display, choices
        self.prefix, self.suffix = prefix, suffix
        self.placeholder = placeholder
        self._set_callback = None
        self._identity = 'cell-' + str(next(_identities))

    def choiceItems(self):
        if isinstance(self.choices, Mapping):
            return self.choices.items()
        return ((value, value) for value in self.choices)

    def set(self, cb, *args, **kwargs):
        self._set_callback = cb, args, kwargs
        return self

    def _set(self, value):
        if self._set_callback:
            cb, args, kwargs = self._set_callback
            cb(value, *args, **kwargs)

    def update(self, prev):
        if prev:
            self._identity = prev._identity
        super().update(prev)

    def releaseRetiredRefs(self):
        self._set_callback = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self._set_callback = None
        super().destroy(direct)


class TableData:
    pui_terminal = False

    def _init_table(self, model, autofit, columnHeader, rowHeader, columnCount, rowCount):
        for name, value in (('columnCount', columnCount), ('rowCount', rowCount)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValueError(name + ' must be a non-negative integer or None')
        self.model, self.autofit = model, autofit
        self.columnHeader, self.rowHeader = columnHeader, rowHeader
        self.columnCount, self.rowCount = columnCount, rowCount
        self.layout_weight = 1
        self.editor = None
        # Adapters expose coordinates, not stable row identities.
        self._generation = object()

    def _dimensions(self):
        if self.model is not None:
            return self.model.rowCount(), self.model.columnCount()
        rows = self.rowCount if self.rowCount is not None else max(len(self.children), len(self.rowHeader or []))
        cols = self.columnCount if self.columnCount is not None else max(
            [len(self.columnHeader or [])] + [len(row.children) for row in self.children])
        return rows, cols

    def _has_header(self, name):
        return getattr(self, name) is not None or (
            self.model is not None and getattr(self.model, name, None) is not None)

    def _header(self, name, index):
        getter = getattr(self.model, name, None) if self.model is not None else None
        if getter is not None:
            return text(resolve(getter(index)))
        labels = getattr(self, name)
        return text(resolve(labels[index])) if labels is not None and index < len(labels) else ''

    def _row_key(self, row):
        if self.model is None and row < len(self.children):
            return self.children[row]._identity
        return ('adapter-' if self.model is not None else 'blank-') + str(row)

    def _cell(self, row, col):
        rows, cols = self._dimensions()
        if not (0 <= row < rows and 0 <= col < cols):
            return None
        if self.model is not None:
            return row, col, None
        if row < len(self.children) and col < len(self.children[row].children):
            return row, col, self.children[row].children[col]
        return None

    def _target(self, info):
        row, col, cell = info
        return cell if cell is not None else (self._generation, row, col)

    def _locate(self, target):
        if self.destroyed:
            return None
        if isinstance(target, TableNode):
            if self.model is not None:
                return None
            cell = target.get_node()
            if cell.destroyed or cell.parent is None:
                return None
            row = cell.parent.get_node()
            if row not in self.children or cell not in row.children:
                return None
            return self._cell(self.children.index(row), row.children.index(cell))
        generation, row, col = target
        if self.model is not None and generation is self._generation:
            return self._cell(row, col)
        return None

    def _raw(self, info):
        row, col, cell = info
        return self.model.editData(row, col) if cell is None else resolve(cell.data)

    def _display(self, info):
        if info is None:
            return ''
        row, col, cell = info
        if cell is None:
            return text(self.model.data(row, col))
        if cell.display is not None:
            value = resolve(cell.display)
        else:
            value = resolve(cell.data)
            if isinstance(cell.choices, Mapping):
                try:
                    value = resolve(cell.choices.get(value, value))
                except TypeError:
                    pass
        return decorate(cell, value)

    def _decorations(self, info):
        return decorations(info[2])

    def _placeholder(self, info):
        return placeholder(info[2])

    def _choices(self, info):
        cell = info[2]
        if cell is None or cell.choices is None:
            return None
        return [(resolve(value), text(resolve(label))) for value, label in cell.choiceItems()]

    def _editable(self, info):
        if info is None:
            return False
        row, col, cell = info
        return self.model.editable(row, col) if cell is None else (
            isinstance(cell.data, BaseBinding) or cell._set_callback is not None)

    def _dispatch(self, info, double=False):
        if info is None:
            return
        row, col, cell = info
        if cell is None:
            (self.model.dblclicked if double else self.model.clicked)(row, col)
        else:
            (cell._dblclicked if double else cell._clicked)(None)

    def _commit(self, info, value):
        root = self.root
        row, col, cell = info
        if cell is None:
            self.model.setData(row, col, value)
        elif isinstance(cell.data, BaseBinding):
            cell.data.value = value
        else:
            cell._set(value)
        if root is not None and not root.destroyed:
            root.redraw()

    def _edit(self, info):
        if self.editor is not None or not self._editable(info):
            return
        value = self._raw(info)
        if self._choices(info) is None and value is not None and type(value) not in (str, int, float, bool):
            return
        self._open_editor(self._target(info), value)

    def _check_editor(self):
        if self.editor is not None and not self.editor.valid():
            self.editor.close()

    def releaseRetiredRefs(self):
        self.editor = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        if self.editor is not None:
            self.editor.close()
        super().destroy(direct)


class CellEdit:
    def __init__(self, table, target, value):
        self.table, self.target, self.original = table, target, value
        info = table._locate(target)
        self.choices = table._choices(info)
        self.decorations = table._decorations(info)
        self.placeholder = table._placeholder(info)
        self.source = self._source(info)
        self.closed = False

    @staticmethod
    def _source(info):
        cell = info[2]
        if cell is None:
            return None
        binding = cell.data
        if isinstance(binding, (AttrBinding, DictBinding, ListBinding)):
            return type(binding), id(binding.state), binding.key
        if isinstance(binding, BaseBinding):
            return id(binding)
        return cell._set_callback

    def valid(self):
        table = self.table.get_node()
        info = table._locate(self.target)
        if self.closed or table.editor is not self or not table._editable(info):
            return False
        value = table._raw(info)
        return (type(value) is type(self.original)
                and (value is self.original or value == self.original)
                and self.source == self._source(info)
                and self.choices == table._choices(info)
                and self.decorations == table._decorations(info)
                and self.placeholder == table._placeholder(info))

    def save_value(self, value):
        if not self.valid():
            self.close()
            return
        try:
            if self.choices is not None:
                if not isinstance(value, int) or not 0 <= value < len(self.choices):
                    raise ValueError('Choose a value.')
                value = self.choices[value][0]
            elif type(self.original) in (int, float):
                try:
                    value = type(self.original)(value)
                except (TypeError, ValueError):
                    raise ValueError('Enter a whole number.' if type(self.original) is int else 'Enter a number.')
            table = self.table.get_node()
            table._commit(table._locate(self.target), value)
        except (TypeError, ValueError) as error:
            if not self.closed:
                self.show_error(str(error))
            return
        self.close()

    def _detach(self):
        self.closed = True
        table = self.table.get_node()
        if table.editor is self:
            table.editor = None
