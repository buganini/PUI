"""Native DataTable / ModalScreen interaction through Textual's headless pilot."""
import contextlib
import io
import unittest

from textual import widgets
from PUI import BaseBinding, BaseTableAdapter, State
from PUI.dom import recur_delete
from PUI.textual import Application, Window, VBox, Table, TableNode


class Value(BaseBinding):
    def __init__(self, value):
        self.value = value


class Example(Application):
    def __init__(self, content):
        super().__init__()
        self.build = content

    def content(self):
        with Window():
            with VBox():
                self.build()


class TextualTableTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = None
        self.output = io.StringIO()
        self.stdout = contextlib.redirect_stdout(self.output)
        self.stderr = contextlib.redirect_stderr(self.output)
        self.stdout.__enter__()
        self.stderr.__enter__()

    async def asyncTearDown(self):
        if self.root:
            # run_test has already unmounted the native tree.
            recur_delete(self.root, self.root, False)
        self.stderr.__exit__(None, None, None)
        self.stdout.__exit__(None, None, None)
        self.assertNotIn('<ERROR', self.output.getvalue(), self.output.getvalue())

    @property
    def table(self):
        return self.root.children[0].children[0].children[0]

    async def sync(self, pilot):
        self.root.redraw()
        await pilot.pause()

    async def edit(self, pilot, row=0, col=0):
        table = self.table
        table.ui.move_cursor(row=row, column=col)
        table.ui.focus()
        await pilot.press('enter')
        await pilot.pause()
        return self.table.editor

    async def save(self, pilot):
        await pilot.click('#table-save')
        await pilot.pause()

    async def test_headers_ragged_literal_text_and_empty_transitions(self):
        rows = [['[red]literal'], ['B', 'C']]
        options = dict(columnHeader=['[bold]One', 'Two', 'Three'], rowHeader=['A', 'B', 'C'])
        def content():
            with Table(**options):
                for row in rows:
                    with TableNode():
                        for value in row:
                            TableNode(value)
        self.root = Example(content)
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            ui = self.table.ui
            self.assertEqual([[v.plain for v in ui.get_row(key)] for key in self.table._rows],
                             [['[red]literal', '', ''], ['B', 'C', ''], ['', '', '']])
            self.assertEqual(ui.ordered_columns[0].label.plain, '[bold]One')
            options.update(rowCount=1, columnCount=1)
            await self.sync(pilot)
            self.assertIs(self.table.ui, ui)
            self.assertEqual((ui.row_count, len(ui.columns)), (1, 1))
            options.clear()
            rows.clear()
            await self.sync(pilot)
            self.assertEqual((ui.row_count, len(ui.columns)), (0, 0))
            rows.append(['again'])
            await self.sync(pilot)
            self.assertEqual(ui.get_row_at(0)[0].plain, 'again')

    async def test_choices_duplicate_labels_typed_values_cancel_and_missing(self):
        value = Value(99)
        choices = {1: '[bold]same', 2: '[bold]same', None: 'None'}
        def content():
            with Table():
                with TableNode():
                    TableNode(value, display='Caption', choices=choices)
                    TableNode('read only', choices=['a', 'b'])
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            editor = await self.edit(pilot)
            self.assertIsInstance(editor.field, widgets.Select)
            self.assertIs(editor.field.value, widgets.Select.NULL)
            await self.save(pilot)
            self.assertFalse(editor.closed)
            self.assertEqual(value.value, 99)
            await pilot.press('escape')
            await pilot.pause()
            self.assertTrue(editor.closed)
            editor = await self.edit(pilot)
            editor.field.value = 1
            await self.save(pilot)
            self.assertIs(type(value.value), int)
            self.assertEqual(value.value, 2)
            self.assertTrue(editor.closed)
            self.assertEqual(self.table.ui.get_cell_at((0, 0)).plain, 'Caption')
            editor = await self.edit(pilot)
            editor.field.value = 2
            await self.save(pilot)
            self.assertIsNone(value.value)
            self.assertIsNone(await self.edit(pilot, 0, 1))

    async def test_native_select_keyboard_and_escape_preserve_model(self):
        value = Value(1)
        def content():
            with Table():
                with TableNode():
                    TableNode(value, choices={1: 'first', 2: 'second'})
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            editor = await self.edit(pilot)
            await pilot.press('enter', 'down', 'enter')
            await pilot.pause()
            self.assertEqual(editor.field.value, 1)  # Index 1 maps to raw integer 2.
            self.assertEqual(value.value, 1)
            await pilot.press('escape')
            await pilot.pause()
            self.assertTrue(editor.closed)
            self.assertEqual(value.value, 1)

    async def test_number_validation_bool_and_empty_choices(self):
        number, boolean = Value(12), Value(False)
        def content():
            with Table():
                with TableNode():
                    TableNode(number)
                    TableNode(boolean)
                    TableNode(number, choices=[])
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            editor = await self.edit(pilot)
            editor.field.value = 'bad'
            await pilot.press('enter')
            await pilot.pause()
            self.assertFalse(editor.closed)
            self.assertEqual(number.value, 12)
            editor.field.value = '42'
            await pilot.press('enter')
            await pilot.pause()
            self.assertTrue(editor.closed)
            self.assertEqual(number.value, 42)
            editor = await self.edit(pilot, 0, 1)
            await pilot.press('space')
            await self.save(pilot)
            self.assertIs(boolean.value, True)
            editor = await self.edit(pilot, 0, 2)
            await self.save(pilot)
            self.assertFalse(editor.closed)
            self.assertEqual(number.value, 42)

    async def test_keyed_reorder_retains_cursor_draft_and_widget(self):
        value = Value('old')
        order = ['edit', 'other']
        def content():
            with Table():
                for key in order:
                    with TableNode().id(key):
                        TableNode(value).id('value')
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            ui = self.table.ui
            editor = await self.edit(pilot)
            await pilot.press('end', '!')
            order.reverse()
            await self.sync(pilot)
            self.assertIs(self.table.ui, ui)
            self.assertIs(self.table.editor, editor)
            self.assertEqual(editor.field.value, 'old!')
            self.assertEqual(ui.cursor_coordinate.row, 1)
            await self.save(pilot)
            self.assertEqual(value.value, 'old!')

    async def test_binding_value_choices_and_removal_invalidate_draft(self):
        state, replacement = State(), State()
        state.value = replacement.value = 'old'
        source = [state]
        options = {}
        visible = [True]
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode(source[0]('value'), **options)
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            editor = await self.edit(pilot)
            source[0] = replacement
            await self.sync(pilot)
            self.assertTrue(editor.closed)
            editor = await self.edit(pilot)
            replacement.value = 'external'
            await pilot.pause()
            self.assertTrue(editor.closed)
            editor = await self.edit(pilot)
            options['choices'] = ['external', 'new']
            await self.sync(pilot)
            self.assertTrue(editor.closed)
            editor = await self.edit(pilot)
            visible[0] = False
            await self.sync(pilot)
            self.assertTrue(editor.closed)
            editor.save()

    async def test_adapter_dialog_refresh_and_dimensions(self):
        class Adapter(BaseTableAdapter):
            values = [[3]]
            def data(self, row, col): return self.values[row][col]
            def setData(self, row, col, value): self.values[row][col] = value
            def editable(self, row, col): return True
            def rowCount(self): return len(self.values)
            def columnCount(self): return len(self.values[0])
        adapter = Adapter()
        self.root = Example(lambda: Table(adapter))
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            self.assertEqual(self.table.ui.ordered_columns[0].label.plain, 'Col 0')
            editor = await self.edit(pilot)
            editor.field.value = '7'
            await self.save(pilot)
            self.assertEqual(adapter.values, [[7]])
            editor = await self.edit(pilot)
            adapter.values = [[8, 9], [1, 2]]
            await self.sync(pilot)
            self.assertTrue(editor.closed)
            self.assertEqual(self.table._dimensions(), (2, 2))

    async def test_callbacks_mouse_and_removal_during_save(self):
        calls, visible = [], [True]
        def save(value):
            calls.append(value)
            visible[0] = False
            self.root.sync()
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode('value').set(save).click(lambda e: calls.append('click')).dblclick(lambda e: calls.append('double'))
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            await pilot.click(self.table.ui, offset=(2, 0))
            self.assertEqual(calls, ['click'])
            self.assertIsNone(self.table.editor)
            await pilot.click(self.table.ui, offset=(2, 0), times=2)
            await pilot.pause()
            self.assertIn('double', calls)
            editor = self.table.editor
            self.assertIsNotNone(editor)
            editor.field.value = 'saved'
            await self.save(pilot)
            self.assertTrue(editor.closed)
            self.assertEqual(calls[-1], 'saved')
            self.assertEqual(self.root.children[0].children[0].children, [])

    async def test_autofit_false_retains_width_and_scroll(self):
        values = ['short'] * 50
        def content():
            with Table(autofit=False):
                for i, value in enumerate(values):
                    with TableNode().id(i):
                        TableNode(value)
        self.root = Example(content)
        async with self.root.ui.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            ui = self.table.ui
            width = ui.ordered_columns[0].width
            ui.scroll_to(y=15, animate=False, force=True, immediate=True)
            await pilot.pause()
            values[0] = 'this is considerably longer than before'
            await self.sync(pilot)
            self.assertEqual(ui.ordered_columns[0].width, width)
            self.assertEqual(ui.scroll_y, 15)

    async def test_headers_navigation_and_programmatic_updates_do_not_edit(self):
        value, calls = Value('before'), []
        options = {}
        def content():
            with Table(columnHeader=['One', 'Two'], rowHeader=['Row'], **options):
                with TableNode():
                    TableNode('read only')
                    TableNode(value).click(lambda e: calls.append('activate'))
        self.root = Example(content)
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            ui = self.table.ui
            await pilot.click(ui, offset=(10, 0))  # Header, not data.
            await pilot.pause()
            self.assertIsNone(self.table.editor)
            ui.focus()
            await pilot.press('right')
            await pilot.pause()
            self.assertEqual(ui.cursor_coordinate.column, 1)
            self.assertEqual(calls, [])
            value.value = 'programmatic'
            await self.sync(pilot)
            self.assertEqual(calls, [])
            await pilot.press('enter')
            await pilot.pause()
            editor = self.table.editor
            self.assertEqual(calls, ['activate'])
            self.assertEqual(editor.field.value, 'programmatic')
            options['columnCount'] = 1
            await self.sync(pilot)
            self.assertTrue(editor.closed)

    async def test_autofit_switch_retains_visible_width(self):
        options = {}
        def content():
            with Table(**options):
                with TableNode():
                    TableNode('a comfortably wide value')
        self.root = Example(content)
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            ui = self.table.ui
            width = ui.ordered_columns[0].get_render_width(ui)
            options['autofit'] = False
            await self.sync(pilot)
            self.assertEqual(ui.ordered_columns[0].get_render_width(ui), width)
            self.assertGreater(ui.ordered_columns[0].width, 0)

    async def test_removal_before_editor_mount_does_not_pop_main_screen(self):
        visible = [True]
        value = Value('initial')
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode(value)
        self.root = Example(content)
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            base_screen = self.root.ui.screen
            table = self.table
            table._edit(table._cell(0, 0))
            editor = table.editor
            visible[0] = False
            self.root.sync()
            await pilot.pause()
            self.assertTrue(editor.closed)
            self.assertIs(self.root.ui.screen, base_screen)
            self.assertEqual(value.value, 'initial')


if __name__ == '__main__':
    unittest.main()
