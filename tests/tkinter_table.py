"""Native Treeview and dialog regression tests; requires a display."""
import contextlib
import io
import unittest
from types import SimpleNamespace
from tkinter import Toplevel
from unittest.mock import patch

from PUI import BaseBinding, BaseTableAdapter, State
from PUI.dom import recur_delete
from PUI.tkinter import Application, Window, VBox, Table, TableNode


class Value(BaseBinding):
    def __init__(self, value):
        self.value = value


class TkTableTests(unittest.TestCase):
    def setUp(self):
        self.root = None
        self.callback_errors = []
        self.output = io.StringIO()
        self.stdout = contextlib.redirect_stdout(self.output)
        self.stdout.__enter__()

    def tearDown(self):
        if self.root is not None:
            recur_delete(self.root, self.root, True)
        self.stdout.__exit__(None, None, None)
        self.assertNotIn('<ERROR', self.output.getvalue(), self.output.getvalue())
        self.assertEqual(self.callback_errors, [])

    def mount(self, content):
        class Example(Application):
            def content(self):
                with Window(size=(600, 400)):
                    with VBox():
                        content()
        self.root = Example()
        self.sync()

    def sync(self):
        self.root.sync()
        self.root.ui.report_callback_exception = lambda *error: self.callback_errors.append(error)
        self.root.ui.update()

    @property
    def table(self):
        return self.root.children[0].children[0].children[0]

    def edit(self, row=0, col=0):
        table = self.table
        table.ui.focus(table._rows[row])
        table._active_column = col
        table._on_enter(None)
        self.root.ui.update()
        return self.table.editor

    def choose(self, editor, index):
        editor.field.current(index)
        editor.field.event_generate('<<ComboboxSelected>>')

    def test_dialog_waits_for_visibility_before_grabbing_and_focusing(self):
        def content():
            with Table():
                with TableNode():
                    TableNode(Value('value'))
        self.mount(content)
        # Hold the window withdrawn to reproduce delayed window-manager mapping.
        with patch.object(Toplevel, 'deiconify'):
            editor = self.edit()
        self.assertFalse(editor.dialog.winfo_viewable())
        self.assertIsNone(editor.dialog.grab_current())
        with patch.object(editor.dialog, 'grab_set', wraps=editor.dialog.grab_set) as grab, \
                patch.object(editor.field, 'focus_set', wraps=editor.field.focus_set) as focus:
            editor.dialog.deiconify()
            self.root.ui.update()
            self.assertTrue(editor.dialog.winfo_viewable())
            self.assertIs(editor.dialog.grab_current(), editor.dialog)
            grab.assert_called_once_with()
            focus.assert_called_once_with()
            # Later visibility changes must not take focus or another modal grab.
            editor.dialog.grab_release()
            editor.field.event_generate('<Visibility>')
            editor.dialog.event_generate('<Visibility>')
            self.root.ui.update()
            self.assertIsNone(editor.dialog.grab_current())
            grab.assert_called_once_with()
            focus.assert_called_once_with()

    def test_removal_before_dialog_visibility_cancels_pending_grab(self):
        visible = [True]
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode(Value('value'))
        self.mount(content)
        with patch.object(Toplevel, 'deiconify'):
            editor = self.edit()
        visible[0] = False
        self.sync()
        self.assertTrue(editor.closed)
        self.assertFalse(editor.dialog.winfo_exists())
        self.assertIsNone(self.root.ui.grab_current())

    def test_ragged_headers_empty_dimensions_and_retained_widths(self):
        rows = [['A'], ['B', 'C']]
        options = dict(columnHeader=['One', 'Two', 'Three'], rowHeader=['First', 'Second', 'Third'])
        def content():
            with Table(**options):
                for row in rows:
                    with TableNode():
                        for value in row:
                            TableNode(value)
        self.mount(content)
        ui = self.table.ui
        self.assertEqual([list(ui.item(key, 'values')) for key in ui.get_children()],
                         [['A', '', ''], ['B', 'C', ''], ['', '', '']])
        self.assertEqual(ui.heading('1', 'text'), 'Two')
        options.update(autofit=False)
        self.sync()
        ui.column('0', width=157)
        self.sync()
        self.assertEqual(ui.column('0', 'width'), 157)
        self.assertIs(self.table.ui, ui)
        options.update(columnCount=1, rowCount=1)
        self.sync()
        self.assertEqual(len(ui.get_children()), 1)
        self.assertEqual(len(ui.cget('columns')), 1)
        options.clear()
        rows.clear()
        self.sync()
        self.assertEqual(ui.get_children(), ())
        self.assertEqual(ui.cget('columns'), '')
        rows.append(['again'])
        self.sync()
        self.assertEqual(ui.item(ui.get_children()[0], 'values'), ('again',))

    def test_choices_types_duplicate_labels_cancel_and_missing_value(self):
        value = Value(99)
        choices = {1: '99', 2: 'same', 3: 'same', None: 'None'}
        def content():
            with Table(columnHeader=['Choice']):
                with TableNode():
                    TableNode(value, display='Caption', choices=choices)
                    TableNode('read only', choices=['a', 'b'])
        self.mount(content)
        editor = self.edit()
        editor.save()
        self.assertFalse(editor.closed)
        self.assertEqual(value.value, 99)
        self.choose(editor, 2)
        editor.close()
        self.assertEqual(value.value, 99)
        editor = self.edit()
        self.choose(editor, 2)
        editor.save()
        self.root.ui.update()
        self.assertEqual(value.value, 3)
        self.assertIs(type(value.value), int)
        self.assertEqual(self.table.ui.item(self.table._rows[0], 'values')[0], 'Caption')
        editor = self.edit()
        self.choose(editor, 3)
        editor.save()
        self.root.ui.update()
        self.assertIsNone(value.value)
        self.assertIsNone(self.edit(0, 1))

    def test_numeric_validation_boolean_and_empty_choices(self):
        number, boolean = Value(12), Value(False)
        def content():
            with Table():
                with TableNode():
                    TableNode(number)
                    TableNode(boolean)
                    TableNode(number, choices=[])
        self.mount(content)
        editor = self.edit()
        editor.field.delete(0, 'end')
        editor.field.insert(0, 'invalid')
        editor.save()
        self.assertFalse(editor.closed)
        self.assertEqual(number.value, 12)
        editor.field.delete(0, 'end')
        editor.field.insert(0, '45')
        editor.save()
        self.root.ui.update()
        self.assertEqual(number.value, 45)
        editor = self.edit(0, 1)
        editor.field.invoke()
        editor.save()
        self.root.ui.update()
        self.assertIs(boolean.value, True)
        editor = self.edit(0, 2)
        editor.save()
        self.assertFalse(editor.closed)
        self.assertEqual(number.value, 45)

    def test_keyed_reorder_selection_and_draft_invalidation(self):
        value = Value('old')
        order = ['edit', 'other']
        editable = [True]
        def content():
            with Table():
                for key in order:
                    with TableNode().id(key):
                        TableNode(value if editable[0] else value.value).id('value')
        self.mount(content)
        old = self.table
        key = old._rows[0]
        old.ui.selection_set(key)
        editor = self.edit()
        editor.field.insert('end', ' draft')
        order.reverse()
        self.sync()
        self.assertIs(self.table.ui, old.get_node().ui)
        self.assertIs(self.table.editor, editor)
        self.assertEqual(self.table.ui.selection(), (key,))
        self.assertEqual(editor.field.get(), 'old draft')
        editor.save()
        self.root.ui.update()
        self.assertEqual(value.value, 'old draft')
        editor = self.edit()
        editable[0] = False
        self.sync()
        self.assertTrue(editor.closed)
        editable[0] = True
        self.sync()
        editor = self.edit()
        order.clear()
        self.sync()
        self.assertTrue(editor.closed)
        editor.save()  # A queued stale callback is harmless.

    def test_rebinding_same_value_and_external_changes_cancel_drafts(self):
        state, replacement = State(), State()
        state.value = replacement.value = 'initial'
        current = [state]
        def content():
            with Table():
                with TableNode():
                    TableNode(current[0]('value'))
        self.mount(content)
        editor = self.edit()
        current[0] = replacement
        self.sync()
        self.assertTrue(editor.closed)
        editor = self.edit()
        replacement.value = 'external'
        self.root.ui.update()
        self.assertTrue(editor.closed)

    def test_adapter_editing_headers_resize_and_stale_draft(self):
        class Adapter(BaseTableAdapter):
            values = [[7]]
            def data(self, row, col): return self.values[row][col]
            def setData(self, row, col, value): self.values[row][col] = value
            def editable(self, row, col): return True
            def rowCount(self): return len(self.values)
            def columnCount(self): return len(self.values[0])
        adapter = Adapter()
        self.mount(lambda: Table(adapter))
        self.assertEqual(self.table.ui.heading('0', 'text'), 'Col 0')
        editor = self.edit()
        editor.field.delete(0, 'end')
        editor.field.insert(0, '9')
        editor.save()
        self.root.ui.update()
        self.assertEqual(adapter.values, [[9]])
        editor = self.edit()
        adapter.values = [[8, 2], [3, 4]]
        self.sync()
        self.assertTrue(editor.closed)
        self.assertEqual(self.table._dimensions(), (2, 2))

    def test_click_callbacks_and_removal_during_save(self):
        events, visible = [], [True]
        def save(value):
            events.append(value)
            visible[0] = False
            self.root.sync()
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode('value').set(save).click(lambda e: events.append('click')).dblclick(lambda e: events.append('double'))
        self.mount(content)
        table = self.table
        x, y, width, height = table.ui.bbox(table._rows[0], '0')
        table.ui.event_generate('<Button-1>', x=x + width // 2, y=y + height // 2)
        self.assertEqual(events, ['click'])
        table._on_double_click(SimpleNamespace(x=x + width // 2, y=y + height // 2))
        self.assertEqual(events, ['click', 'double'])
        editor = table.editor
        editor.field.insert('end', '!')
        editor.save()
        self.root.ui.update()
        self.assertTrue(editor.closed)
        self.assertEqual(events[-1], 'value!')
        self.assertEqual(self.root.children[0].children[0].children, [])

    def test_options_reject_invalid_counts_and_choices(self):
        for value in (-1, True, 1.5):
            with self.assertRaises(ValueError): Table(columnCount=value)
            with self.assertRaises(ValueError): Table(rowCount=value)
        with self.assertRaises(TypeError): TableNode(choices='abc')

    def test_native_enter_escape_and_table_removal_close_dialog(self):
        value = Value('unchanged')
        visible = [True]
        def content():
            if visible[0]:
                with Table():
                    with TableNode():
                        TableNode(value)
        self.mount(content)
        self.table.ui.focus(self.table._rows[0])
        self.table.ui.focus_force()
        self.root.ui.update()
        self.table.ui.event_generate('<Return>')
        self.root.ui.update()
        editor = self.table.editor
        self.assertIsNotNone(editor)
        editor.field.focus_force()
        self.root.ui.update()
        editor.field.event_generate('<Escape>')
        self.root.ui.update()
        self.assertTrue(editor.closed)
        self.assertEqual(value.value, 'unchanged')
        editor = self.edit()
        visible[0] = False
        self.sync()
        self.assertTrue(editor.closed)


if __name__ == '__main__':
    unittest.main()
