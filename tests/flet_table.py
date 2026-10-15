"""env/bin/python -m unittest discover -s tests -p flet_table.py -v"""
import asyncio
import contextlib
import io
import unittest

import flet as ft
import msgpack
from flet.messaging.session import Session
from flet_regression import RecordingConnection
from PUI.dom import recur_delete
from PUI.flet import Application, Window, Table, TableNode, BaseBinding, BaseTableAdapter


class Value(BaseBinding):
    def __init__(self, value):
        self.value = value


class FletTableTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = RecordingConnection(asyncio.get_running_loop())
        self.session = Session(self.connection)
        # Native client registration mounts services/dialogs and captures snapshots.
        msgpack.packb(self.session.get_page_patch(), default=self.connection.encoder)
        self.root = None

    async def asyncTearDown(self):
        if self.root is not None:
            recur_delete(self.root, self.root, True)
        await asyncio.sleep(0)

    async def mount(self, content):
        class Example(Application):
            def content(self):
                with Window():
                    content()
        self.root = Example()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            await self.root.flet_app(self.session.page)
        self.assertNotIn('<ERROR', output.getvalue())

    @property
    def table(self):
        return self.root.children[0].children[0]

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue())
        if self.table.hscroll.controls:
            self.table.ui.before_update()

    async def event(self, control, name):
        with self.assertNoLogs('flet', level='ERROR'):
            await self.session.dispatch_event(control._i, name, None)
            await asyncio.sleep(0)

    async def edit(self, row=0, col=0):
        await self.event(self.table.ui.rows[row].cells[col], 'tap')
        self.assertIsNotNone(self.table.editor)
        return self.table.editor

    async def test_ragged_counts_headers_and_empty_transitions(self):
        data = [['a'], ['b', 'c']]
        options = dict(columnHeader=['A', 'B', 'C'], rowHeader=['One', 'Two', 'Three'])
        def content():
            with Table(**options):
                for row in data:
                    with TableNode():
                        for cell in row:
                            TableNode(cell)
        await self.mount(content)
        table = self.table
        native_table = table.ui
        table.ui.before_update()
        self.assertEqual(len(table.ui.columns), 4)
        self.assertEqual([[c.content for c in r.cells] for r in table.ui.rows],
                         [['One', 'a', '', ''], ['Two', 'b', 'c', ''], ['Three', '', '', '']])
        blank = table.ui.rows[0].cells[2]
        self.assertIsNone(blank.on_tap)
        options.update(columnCount=1, rowCount=1)
        self.sync()
        self.assertEqual(len(self.table.ui.rows), 1)
        self.assertEqual(len(self.table.ui.columns), 2)
        options.clear()
        data.clear()
        self.sync()
        self.assertIs(self.table.ui, native_table)
        self.assertEqual(self.table.hscroll.controls, [])
        options['columnHeader'] = ['A']
        self.sync()
        self.assertEqual(self.table.ui.rows, [])
        self.assertEqual(self.table.hscroll.controls, [native_table])
        options.clear()
        data.append(['no header'])
        self.sync()
        self.assertEqual(self.table.ui.heading_row_height, 0)

    async def test_choices_preserve_types_duplicate_labels_and_readonly(self):
        value = Value(99)
        def content():
            with Table():
                with TableNode():
                    TableNode(value, choices={3: 'Same', 4: 'Same'})
                    TableNode(3, choices={3: 'Readonly'})
        await self.mount(content)
        dropdown = self.table.ui.rows[0].cells[0].content
        self.assertIsInstance(dropdown, ft.Dropdown)
        self.assertIsNone(self.table.ui.rows[0].cells[0].on_tap)
        self.assertIsNone(self.table.ui.rows[0].cells[0].on_double_tap)
        self.assertIsNone(dropdown.value)
        self.assertEqual(dropdown.hint_text, '99')
        self.assertEqual([o.key for o in dropdown.options], ['0', '1'])
        self.assertEqual(self.table.ui.rows[0].cells[1].content, 'Readonly')
        dropdown.value = '1'
        await self.event(dropdown, 'select')
        self.assertEqual(value.value, 4)
        self.assertIs(type(value.value), int)
        self.assertIs(self.table.ui.rows[0].cells[0].content, dropdown)
        await self.event(self.table.ui.rows[0].cells[1], 'tap')
        self.assertIsNone(self.table.editor)

    async def test_decorated_choice_keeps_dropdown_and_commits_raw_value(self):
        value = Value(3)
        def content():
            with Table():
                with TableNode():
                    TableNode(value, choices={3: 'Three', 4: 'Four'},
                              prefix='Choice: [', suffix=']',
                              placeholder='Choose number')
        await self.mount(content)
        row = self.table.ui.rows[0].cells[0].content
        self.assertIsInstance(row, ft.Row)
        dropdown = next(control for control in row.controls if isinstance(control, ft.Dropdown))
        self.assertEqual(dropdown.hint_text, 'Choose number')
        self.assertEqual([control.value for control in row.controls if isinstance(control, ft.Text)],
                         ['Choice: [', ']'])
        dropdown.value = '1'
        await self.event(dropdown, 'select')
        self.assertEqual(value.value, 4)
        self.assertIs(next(control for control in self.table.ui.rows[0].cells[0].content.controls
                           if isinstance(control, ft.Dropdown)), dropdown)

    async def test_dialog_uses_raw_value_cancel_save_and_normalized_display(self):
        value = Value('raw')
        calls = []
        def save(data, suffix):
            calls.append(data)
            value.value = data.strip() + suffix
        def content():
            with Table():
                with TableNode():
                    TableNode(value.value, display='Shown: ' + value.value,
                              prefix='Price: $', suffix=' USD',
                              placeholder='Enter price').set(save, '!')
        await self.mount(content)
        self.assertEqual(self.table.ui.rows[0].cells[0].content, 'Price: $Shown: raw USD')
        editor = await self.edit()
        self.assertEqual(editor.field.value, 'raw')
        self.assertEqual(editor.field.hint_text, 'Enter price')
        self.assertEqual(editor.decorations, ('Price: $', ' USD'))
        row = editor.dialog.content.controls[0]
        self.assertEqual([control.value for control in row.controls if isinstance(control, ft.Text)],
                         ['Price: $', ' USD'])
        editor.field.value = 'discard'
        await self.event(editor.dialog.actions[0], 'click')
        self.assertFalse(editor.dialog.open)
        self.assertIsNone(self.table.editor)
        self.assertEqual(calls, [])
        await self.event(editor.dialog, 'dismiss')
        editor = await self.edit()
        editor.field.value = ' changed '
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(calls, [' changed '])
        self.assertEqual(self.table.ui.rows[0].cells[0].content, 'Price: $Shown: changed! USD')
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(len(calls), 1)

    async def test_numeric_validation_and_boolean_editor(self):
        values = [Value(2), Value(1.5), Value(False), Value(None)]
        def content():
            with Table():
                with TableNode():
                    for value in values:
                        TableNode(value)
        await self.mount(content)
        editor = await self.edit()
        editor.field.value = '2.3'
        message_count = len(self.connection.messages)
        await self.event(editor.field, 'submit')
        self.assertTrue(editor.dialog.open)
        self.assertEqual(values[0].value, 2)
        self.assertEqual(editor.field.error, 'Enter a whole number.')
        self.assertIn('Enter a whole number.', repr(self.connection.messages[message_count:]))
        editor.field.value = '42'
        await self.event(editor.field, 'submit')
        self.assertEqual(values[0].value, 42)
        for col, draft, expected in [(1, '2.75', 2.75), (2, True, True), (3, 'new', 'new')]:
            editor = await self.edit(col=col)
            editor.field.value = draft
            await self.event(editor.dialog.actions[1], 'click')
            self.assertEqual(values[col].value, expected)
            self.assertIs(type(values[col].value), type(expected))

    async def test_keyed_rows_and_cells_keep_draft_and_current_callback(self):
        rows, columns = ['a', 'b'], ['x', 'y']
        calls, version = [], [1]
        def content():
            with Table():
                for r in rows:
                    with TableNode().id(r):
                        for c in columns:
                            TableNode(r + c).id(c).set(lambda v, r=r, c=c, n=version[0]: calls.append((r, c, n, v)))
        await self.mount(content)
        original = self.table.ui.rows[0].cells[0]
        editor = await self.edit()
        editor.field.value = 'draft'
        rows.reverse()
        columns.reverse()
        version[0] = 2
        self.sync()
        self.assertIs(self.table.ui.rows[1].cells[1], original)
        self.assertIs(self.table.editor, editor)
        self.assertEqual(editor.field.value, 'draft')
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(calls, [('a', 'x', 2, 'draft')])

    async def test_removal_source_change_and_editability_cancel_draft(self):
        value, rows, editable = Value('one'), [1], [True]
        def content():
            with Table():
                for r in rows:
                    with TableNode().id(r):
                        TableNode(value if editable[0] else value.value)
        await self.mount(content)
        editor = await self.edit()
        value.value = 'external'
        self.sync()
        self.assertFalse(editor.dialog.open)
        editor.field.value = 'stale'
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(value.value, 'external')
        editor = await self.edit()
        editable[0] = False
        self.sync()
        self.assertFalse(editor.dialog.open)
        editable[0] = True
        self.sync()
        editor = await self.edit()
        rows.clear()
        self.sync()
        self.assertFalse(editor.dialog.open)
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(value.value, 'external')

    async def test_callbacks_rebind_clear_and_keep_logical_indices(self):
        calls, version = [], [1]
        def content():
            with Table(rowHeader=['Header']):
                with TableNode():
                    node = TableNode('cell')
                    if version[0]:
                        node.click(lambda e, n=version[0]: calls.append(('click', n)))
                        node.dblclick(lambda e, n=version[0]: calls.append(('double', n)))
        await self.mount(content)
        native = self.table.ui.rows[0].cells[1]
        await self.event(native, 'tap')
        version[0] = 2
        self.sync()
        await self.event(native, 'double_tap')
        version[0] = None
        self.sync()
        await self.event(native, 'tap')
        self.assertEqual(calls, [('click', 1), ('double', 2)])

    async def test_adapter_display_edit_refresh_and_stale_indices(self):
        class Adapter(BaseTableAdapter):
            rows = [[1], [2]]
            calls = []
            def rowCount(self): return len(self.rows)
            def columnCount(self): return len(self.rows[0]) if self.rows else 0
            def data(self, r, c): return f'Value: {self.rows[r][c]}'
            def editData(self, r, c): return self.rows[r][c]
            def editable(self, r, c): return r == 0
            def setData(self, r, c, value):
                self.calls.append(('set', r, c, value))
                self.rows[r][c] = max(value, 0)
            def clicked(self, r, c): self.calls.append(('click', r, c))
            def dblclicked(self, r, c): self.calls.append(('double', r, c))
        adapter = Adapter()
        await self.mount(lambda: Table(adapter))
        editor = await self.edit(col=1)
        self.assertEqual(editor.field.value, '1')
        editor.field.value = '-2'
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(adapter.calls, [('click', 0, 0), ('set', 0, 0, -2)])
        self.assertEqual(self.table.ui.rows[0].cells[1].content, 'Value: 0')
        await self.event(self.table.ui.rows[1].cells[1], 'double_tap')
        self.assertEqual(adapter.calls[-1], ('double', 1, 0))
        self.assertIsNone(self.table.editor)
        editor = await self.edit(col=1)
        adapter.rows.reverse()
        self.sync()
        self.assertFalse(editor.dialog.open)
        editor.field.value = '100'
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(adapter.rows, [[2], [0]])
        adapter.rows[0].append(3)
        adapter.rows[1].append(4)
        self.sync()
        self.assertEqual(len(self.table.ui.columns), 3)

    async def test_table_removal_closes_own_dialog_only(self):
        visible = [True]
        value = Value('old')
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode(value)
        await self.mount(content)
        editor = await self.edit()
        other = ft.AlertDialog(title=ft.Text('Other'))
        self.session.page.show_dialog(other)
        visible[0] = False
        self.root.sync()
        self.assertFalse(editor.dialog.open)
        self.assertTrue(other.open)
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(value.value, 'old')

    async def test_choice_caption_style_reset_and_editor_removal(self):
        value, styled, editable = Value(3), [True], [True]
        def content():
            table = Table()
            if styled[0]:
                table.style(color=0, fontSize=18)
            with table:
                with TableNode():
                    TableNode(value if editable[0] else value.value,
                              display='Caption', choices={3: 'Three', 4: 'Four'})
        await self.mount(content)
        dropdown = self.table.ui.rows[0].cells[0].content
        self.assertEqual(dropdown.label, 'Caption')
        self.assertEqual(dropdown.options[0].text, 'Three')
        self.assertEqual(dropdown.text_style.color, '#000000')
        styled[0] = False
        self.sync()
        self.assertIsNone(dropdown.text_style.color)
        editable[0] = False
        self.sync()
        self.assertEqual(self.table.ui.rows[0].cells[0].content, 'Caption')
        dropdown.value = '1'
        await self.event(dropdown, 'select')
        self.assertEqual(value.value, 3)

    async def test_save_callback_can_synchronously_remove_table(self):
        visible, saved = [True], []
        def save(value):
            saved.append(value)
            visible[0] = False
            self.root.sync()
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode('original').set(save)
        await self.mount(content)
        editor = await self.edit()
        editor.field.value = 'saved'
        await self.event(editor.dialog.actions[1], 'click')
        self.assertEqual(saved, ['saved'])
        self.assertFalse(editor.dialog.open)
        self.assertEqual(self.root.children[0].children, [])

    def test_invalid_options(self):
        for value in [-1, True, 1.5]:
            with self.assertRaises(ValueError):
                Table(rowCount=value)
        with self.assertRaises(NotImplementedError):
            Table(autofit=False)
        for value in ['abc', {1, 2}, 12]:
            with self.assertRaises(TypeError):
                TableNode(choices=value)


if __name__ == '__main__':
    unittest.main()
