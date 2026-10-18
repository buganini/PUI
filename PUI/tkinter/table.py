from __future__ import annotations
from .. import _typing as _t
from .base import TkBaseWidget, tk, ttk, tkFont
from .._table import CellEdit, TableData, TableNode, text


class Table(TableData, TkBaseWidget):
    ttk_style = 'Treeview'
    expand_x_prio = expand_y_prio = 3

    def __init__(self, model: _t.Any = None, autofit: bool = True, columnHeader: _t.Sequence[_t.Any] | None = None,
                 rowHeader: _t.Sequence[_t.Any] | None = None, columnCount: int | None = None, rowCount: int | None = None) -> None:
        super().__init__()
        self._init_table(model, autofit, columnHeader, rowHeader, columnCount, rowCount)

    @property
    def outer(self):
        return self.frame

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.frame = prev.ui, prev.frame
            self.editor = prev.editor
            self._active_column = prev._active_column
        else:
            self.frame = ttk.Frame(self.tkparent.inner)
            self.frame.grid_rowconfigure(0, weight=1)
            self.frame.grid_columnconfigure(0, weight=1)
            self.ui = ttk.Treeview(self.frame, selectmode='browse')
            self.ui.grid(row=0, column=0, sticky='nsew')
            vertical = ttk.Scrollbar(self.frame, orient='vertical', command=self.ui.yview)
            horizontal = ttk.Scrollbar(self.frame, orient='horizontal', command=self.ui.xview)
            vertical.grid(row=0, column=1, sticky='ns')
            horizontal.grid(row=1, column=0, sticky='ew')
            self.ui.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
            self._active_column = 0
            self.ui.bind('<Button-1>', self._on_click)
            self.ui.bind('<Double-1>', self._on_double_click)
            self.ui.bind('<Return>', self._on_enter)
        super().update(prev)

    def postSync(self):
        rows, cols = self._dimensions()
        columns = tuple(str(c) for c in range(cols))
        if tuple(self.ui.cget('columns')) != columns:
            old_widths = {c: self.ui.column(c, 'width') for c in self.ui.cget('columns')}
            self.ui.configure(columns=columns)
            for c in columns:
                self.ui.column(c, width=old_widths.get(c, 100), stretch=False)
        show = []
        if self._has_header('rowHeader'):
            show.append('tree')
        if self._has_header('columnHeader'):
            show.append('headings')
        self.ui.configure(show=show)
        self.ui.heading('#0', text='')
        self.ui.column('#0', stretch=False)
        for c in range(cols):
            self.ui.heading(str(c), text=self._header('columnHeader', c))
        self._rows = [self._row_key(r) for r in range(rows)]
        wanted = set(self._rows)
        for key in self.ui.get_children():
            if key not in wanted:
                self.ui.delete(key)
        values = []
        for r, key in enumerate(self._rows):
            row = [self._display(self._cell(r, c)) for c in range(cols)]
            values.append(row)
            options = dict(text=self._header('rowHeader', r), values=row)
            if self.ui.exists(key):
                self.ui.item(key, **options)
                self.ui.move(key, '', r)
            else:
                self.ui.insert('', r, iid=key, **options)
        if self.autofit:
            style = ttk.Style(self.ui)
            font = tkFont.Font(root=self.ui, font=style.lookup(self.ui.cget('style'), 'font') or 'TkDefaultFont')
            heading_font = tkFont.Font(root=self.ui, font=style.lookup('Treeview.Heading', 'font') or 'TkDefaultFont')
            for c in range(cols):
                width = max([heading_font.measure(self._header('columnHeader', c))]
                            + [font.measure(row[c]) for row in values]) + 20
                self.ui.column(str(c), width=max(20, width))
            self.ui.column('#0', width=max([20] + [font.measure(self._header('rowHeader', r)) + 20 for r in range(rows)]))
        self._check_editor()

    def _pointer(self, event, double=False):
        node = self.get_node()
        if node.destroyed or node.ui.identify_region(event.x, event.y) != 'cell':
            return
        key = node.ui.identify_row(event.y)
        column = node.ui.identify_column(event.x)
        if key not in node._rows or not column:
            return
        col = int(column[1:]) - 1
        info = node._cell(node._rows.index(key), col)
        if info is None:
            return
        target = node._target(info)
        node._preClicked()
        node = node.get_node()
        info = node._locate(target)
        if info is None:
            return
        node._active_column = col
        node._dispatch(info, double)
        if double:
            node = node.get_node()
            node._edit(node._locate(target))

    def _on_click(self, event):
        self._pointer(event)

    def _on_double_click(self, event):
        self._pointer(event, True)
        return 'break'

    def _on_enter(self, event):
        node = self.get_node()
        if not node.destroyed:
            key = node.ui.focus()
            if key in node._rows:
                cols = node._dimensions()[1]
                node._edit(node._cell(node._rows.index(key), min(node._active_column, cols - 1)))
        return 'break'

    def _open_editor(self, target, value):
        self.editor = _CellEditor(self, target, value)
        self.editor.show()

    def releaseRetiredRefs(self):
        self.frame = None
        super().releaseRetiredRefs()


class _CellEditor(CellEdit):
    def __init__(self, table, target, value):
        super().__init__(table, target, value)
        self.dialog = tk.Toplevel(table.ui)
        self.dialog.withdraw()
        self.dialog.title('Edit cell')
        self.dialog.transient(table.ui.winfo_toplevel())
        self.dialog.protocol('WM_DELETE_WINDOW', self.close)
        body = ttk.Frame(self.dialog, padding=12)
        body.grid(sticky='nsew')
        self.dialog.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        decorated = any(self.decorations)
        field_parent = ttk.Frame(body) if decorated else body
        if self.choices is not None:
            self.field = ttk.Combobox(field_parent, state='readonly', values=[label for _, label in self.choices])
            index = next((i for i, (item, _) in enumerate(self.choices) if item == value), -1)
            self.choice_index = index
            self.field.bind('<<ComboboxSelected>>', self._choose)
            if index >= 0:
                self.field.current(index)
            else:
                self.field.set(text(value))
        elif type(value) is bool:
            self.variable = tk.BooleanVar(field_parent, value=value)
            self.field = ttk.Checkbutton(field_parent, text='' if decorated else 'Value', variable=self.variable)
        else:
            self.field = ttk.Entry(field_parent)
            self.field.insert(0, text(value))
        if decorated:
            column = 0
            if self.decorations[0]:
                ttk.Label(field_parent, text=self.decorations[0]).grid(row=0, column=column, sticky='w')
                column += 1
            self.field.grid(row=0, column=column, sticky='ew')
            field_parent.grid_columnconfigure(column, weight=1)
            column += 1
            if self.decorations[1]:
                ttk.Label(field_parent, text=self.decorations[1]).grid(row=0, column=column, sticky='w')
            field_parent.grid(row=0, column=0, columnspan=2, sticky='ew')
        else:
            self.field.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.error = ttk.Label(body, text='', foreground='red')
        self.error.grid(row=1, column=0, columnspan=2, sticky='w')
        ttk.Button(body, text='Cancel', command=self.close).grid(row=2, column=0, sticky='e', pady=(8, 0))
        ttk.Button(body, text='Save', command=self.save).grid(row=2, column=1, sticky='e', pady=(8, 0))
        self.dialog.bind('<Escape>', lambda event: self.close())
        self.dialog.bind('<Return>', lambda event: self.save())

    def show(self):
        # Mapping is asynchronous; grab_set requires a viewable window.
        self._visibility_binding = self.dialog.bind('<Visibility>', self._on_visibility)
        self.dialog.deiconify()

    def _on_visibility(self, event):
        if self.closed or event.widget is not self.dialog or not self.dialog.winfo_viewable():
            return
        self.dialog.unbind('<Visibility>', self._visibility_binding)
        self.dialog.grab_set()
        self.field.focus_set()

    def show_error(self, message):
        self.error.configure(text=message)

    def save(self):
        if self.closed:
            return
        if self.choices is not None:
            value = self.choice_index
        elif type(self.original) is bool:
            value = self.variable.get()
        else:
            value = self.field.get()
        self.save_value(value)

    def _choose(self, event):
        self.choice_index = self.field.current()

    def close(self):
        if self.closed:
            return
        self._detach()
        try:
            self.dialog.destroy()
            table = self.table.get_node()
            if not table.destroyed and table.ui is not None:
                table.ui.focus_set()
        except tk.TclError:
            pass  # The owner window may already have been destroyed.
