"""HTML table data and validated, cell-scoped inline edits."""
from copy import deepcopy
import math

from .._table import TableData, TableNode, CellEdit, text
from ..state import ListBinding, DictBinding, Unstate
from .widgets import WebNode


class Table(TableData, WebNode):
    wire_type = 'Table'
    native_event = 'table'

    def __init__(self, model=None, autofit=True, columnHeader=None,
                 rowHeader=None, columnCount=None, rowCount=None):
        super().__init__()
        self._init_table(model, autofit, columnHeader, rowHeader, columnCount, rowCount)
        self._cells = {}

    def update(self, prev):
        if prev is not None:
            self._cells = prev._cells
        super().update(prev)

    # TableNode children are data declarations, not standalone Web elements.
    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def _context(self, info):
        cell = info[2]
        binding = cell.data if cell is not None else None
        generation = (binding.state._binding_generation(binding.key)
                      if isinstance(binding, (ListBinding, DictBinding)) else None)
        raw, choices = deepcopy(Unstate(self._raw(info))), deepcopy(self._choices(info))
        generation = (generation, type(raw), None if choices is None else tuple(type(v) for v, _ in choices))
        return (CellEdit._source(info) if cell is not None else self._generation, generation,
                self._editable(info), raw, choices)

    def properties(self):
        rows, cols = self._dimensions()
        if (type(rows) is not int or type(cols) is not int or min(rows, cols) < 0 or
                max(rows, cols) > 10000 or rows * cols > 10000):
            raise ValueError('Web Table supports at most 10000 cells')
        previous, current, rendered = self._cells, {}, []
        for r in range(rows):
            row = []
            for c in range(cols):
                info = self._cell(r, c)
                if info is None:
                    row.append(None)
                    continue
                target = self._target(info)
                key = info[2]._identity if info[2] is not None else (r, c)
                context = self._context(info)
                entry = previous.get(key)
                if entry is None or entry['context'] != context:
                    entry = dict(target=target, context=context, token=self.runtime.identifier('cell'), seq=0, error='')
                entry['target'] = target
                current[key] = entry
                raw, choices = context[3:]
                editor = None
                value = None
                if context[2]:
                    if choices is not None:
                        editor = 'choice'
                        value = next((i for i, (v, _) in enumerate(choices) if type(v) is type(raw) and v == raw), None)
                    elif type(raw) is bool:
                        editor, value = 'bool', raw
                    elif raw is None or type(raw) in (str, int, float):
                        editor, value = 'text', text(raw)
                row.append(dict(token=entry['token'], text=self._display(info), editor=editor,
                                value=value, choices=[] if choices is None else [label for _, label in choices],
                                error=entry['error']))
            rendered.append(dict(id=self._row_key(r), cells=row))
        self._cells = current
        return dict(rows=rendered, columns=[self._header('columnHeader', c) for c in range(cols)],
                    column_header=self._has_header('columnHeader'),
                    row_headers=[self._header('rowHeader', r) for r in range(rows)] if self._has_header('rowHeader') else None,
                    autofit=bool(self.autofit))

    def handle_native(self, data):
        entry = next((e for e in self._cells.values() if e['token'] == data['cell']), None)
        if entry is None:
            return False
        info = self._locate(entry['target'])
        if info is None:
            return False
        try:
            if entry['context'] != self._context(info):
                return False
        except (IndexError, KeyError, AttributeError):
            return False
        if data['action'] != 'commit':
            self._dispatch(info, double=data['action'] == 'dblclick')
            return True
        if not self._editable(info) or data['edit_seq'] <= entry['seq']:
            return False
        entry['seq'] = data['edit_seq']
        raw, choices = entry['context'][3:]
        value = data['value']
        try:
            if choices is not None:
                if type(value) is not int or not 0 <= value < len(choices):
                    raise ValueError('Choose a value.')
                value = choices[value][0]
            elif type(raw) is bool:
                if type(value) is not bool:
                    raise ValueError('Choose true or false.')
            elif raw is None or type(raw) in (str, int, float):
                if type(value) is not str:
                    raise ValueError('Enter text.')
                if type(raw) in (int, float):
                    value = type(raw)(value)
                    if type(value) is float and not math.isfinite(value):
                        raise ValueError('Enter a finite number.')
            else:
                return False
            self._commit(info, value)
        except (ValueError, TypeError) as error:
            entry['error'] = str(error)
        else:
            entry['error'] = ''
        return True

    def reset_connection(self):
        self._cells = {}

    def releaseRetiredRefs(self):
        self._cells = {}
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self._cells.clear()
        super().destroy(direct)
