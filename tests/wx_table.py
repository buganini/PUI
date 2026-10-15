"""python3 -m unittest discover -s tests -p wx_table.py -v (GUI required)."""
import contextlib
import io
import unittest

import wx
import wx.grid as gridlib
from PUI.wx import Application, Window, Table, TableNode, State, BaseTableAdapter
from PUI.dom import recur_delete


class WxTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()

    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root is not None and not self.root.destroyed:
            recur_delete(self.root, self.root, True)
        for window in wx.GetTopLevelWindows():
            window.Destroy()
        self.pump()

    def pump(self):
        for _ in range(4):
            self.app.Yield()
            self.app.ProcessPendingEvents()

    def mount(self, root):
        self.root = root
        self.sync()
        root.children[0].ui.Show()
        self.pump()
        return root.children[0].children[0]

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())

    def editor(self, grid, row, col):
        grid.SetFocus()
        self.pump()
        grid.SetGridCursor(row, col)
        grid.EnableCellEditControl()
        self.assertTrue(grid.IsCellEditControlEnabled())
        return grid.GetCellEditor(row, col)

    def test_ragged_headers_dimensions_empty_and_autofit(self):
        class Example(Application):
            rows = [['a'], ['b', 'c']]
            headers = ['one', 'two', 'three']
            def content(self):
                with Window(size=(600, 400)):
                    with Table(columnHeader=self.headers, rowHeader=['r1', 'r2'], autofit=False):
                        for row in self.rows:
                            with TableNode():
                                for value in row:
                                    TableNode(value)
        table = self.mount(Example())
        grid = table.ui
        self.assertEqual((grid.GetNumberRows(), grid.GetNumberCols()), (2, 3))
        self.assertEqual(grid.GetCellValue(1, 1), 'c')
        self.assertEqual(grid.GetCellValue(0, 2), '')
        self.assertTrue(grid.IsReadOnly(0, 2))
        grid.SetColSize(0, 173)
        self.sync()
        self.assertEqual(grid.GetColSize(0), 173)
        self.root.rows = []
        self.root.headers = None
        self.sync()
        self.assertEqual(grid.GetNumberCols(), 0)
        self.assertEqual(grid.GetColLabelSize(), 0)
        self.root.rows = [['back']]
        self.root.headers = ['again']
        self.sync()
        self.assertEqual(grid.GetCellValue(0, 0), 'back')
        self.assertGreater(grid.GetColLabelSize(), 0)
        self.assertEqual(grid.GetColLabelValue(0), 'again')

    def test_text_numeric_validation_and_display_separation(self):
        class Example(Application):
            def __init__(self):
                super().__init__()
                self.state = State()
                self.state.number = 7
            def content(self):
                with Window(size=(500, 300)):
                    with Table():
                        with TableNode():
                            TableNode(self.state('number'), display=self.state.number,
                                      prefix='Price: $', suffix=' USD',
                                      placeholder='Enter price')
        table = self.mount(Example())
        grid = table.ui
        self.assertEqual(grid.GetCellValue(0, 0), 'Price: $7 USD')
        editor = self.editor(grid, 0, 0)
        self.assertIsInstance(editor.GetControl(), wx.Panel)
        self.assertEqual(editor.field.GetValue(), '7')
        self.assertEqual(editor.field.GetHint(), 'Enter price')
        self.assertEqual([label.GetLabel() for label in editor.GetControl().GetChildren()
                          if isinstance(label, wx.StaticText)], ['Price: $', ' USD'])
        editor.field.ChangeValue('not a number')
        grid.SaveEditControlValue()
        grid.DisableCellEditControl()
        self.assertEqual(self.root.state.number, 7)
        editor.DecRef()
        editor = self.editor(grid, 0, 0)
        editor.field.ChangeValue('12')
        grid.SaveEditControlValue()
        grid.DisableCellEditControl()
        self.pump()
        self.assertEqual(self.root.state.number, 12)
        self.assertIsInstance(self.root.state.number, int)
        self.assertEqual(grid.GetCellValue(0, 0), 'Price: $12 USD')
        editor.DecRef()

    def test_duplicate_choice_labels_preserve_raw_types_and_unknown(self):
        received = []
        class Example(Application):
            value = 'unknown'
            def content(self):
                with Window(size=(500, 300)):
                    with Table():
                        with TableNode():
                            TableNode(self.value, choices={1: 'same', '1': 'same'}).set(received.append)
                            TableNode(1, choices=[1, 2])
        table = self.mount(Example())
        grid = table.ui
        self.assertTrue(grid.IsReadOnly(0, 1))
        editor = self.editor(grid, 0, 0)
        choice = editor.GetControl()
        self.assertIsInstance(choice, wx.Choice)
        self.assertEqual(choice.GetSelection(), wx.NOT_FOUND)
        self.assertEqual(choice.GetItems(), ['same', 'same'])
        choice.SetSelection(1)
        choice.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_CHOICE, choice.GetId()))
        self.assertFalse(grid.IsCellEditControlEnabled())
        self.pump()
        self.assertEqual(received, ['1'])
        self.assertIsInstance(received[0], str)
        editor.DecRef()
        editor = self.editor(grid, 0, 0)
        editor.GetControl().SetSelection(0)
        grid.SaveEditControlValue()
        grid.DisableCellEditControl()
        self.pump()
        self.assertEqual(received, ['1', 1])
        editor.DecRef()

    def test_reconcile_cancels_draft_and_callbacks_follow_keyed_cells(self):
        received, clicked = [], []
        class Example(Application):
            order = ['a', 'b']
            version = 0
            show = True
            def content(self):
                with Window(size=(500, 300)):
                    if self.show:
                        with Table():
                            for key in self.order:
                                with TableNode().id(key):
                                    TableNode(key).set(received.append).click(
                                        lambda e, name, version: clicked.append((name, version)), key, self.version)
        old = self.mount(Example())
        grid = old.ui
        editor = self.editor(grid, 0, 0)
        editor.GetControl().ChangeValue('stale')
        self.root.order = ['b', 'a']
        self.root.version = 1
        self.sync()
        self.assertFalse(grid.IsCellEditControlEnabled())
        self.assertEqual(received, [])
        self.assertIsNone(editor.EndEdit(0, 0, grid, 'a'))
        editor.DecRef()
        event = gridlib.GridEvent(grid.GetId(), gridlib.wxEVT_GRID_CELL_LEFT_CLICK, grid, 1, 0)
        grid.GetEventHandler().ProcessEvent(event)
        self.assertEqual(clicked, [('a', 1)])
        editor = self.editor(grid, 0, 0)
        editor.GetControl().ChangeValue('removed draft')
        editor.DecRef()
        self.root.show = False
        self.sync()
        self.pump()
        self.assertEqual(received, [])
        old.on_click(event)
        self.assertEqual(clicked, [('a', 1)])

    def test_adapter_refresh_edit_headers_and_resize(self):
        class Adapter(BaseTableAdapter):
            values = [[1.5]]
            rowHeader = None
            def rowCount(self): return len(self.values)
            def columnCount(self): return len(self.values[0]) if self.values else 0
            def data(self, row, col): return f'Value {self.values[row][col]}'
            def editData(self, row, col): return self.values[row][col]
            def editable(self, row, col): return True
            def setData(self, row, col, value): self.values[row][col] = round(value, 1)
        adapter = Adapter()
        class Example(Application):
            def content(self):
                with Window(size=(500, 300)):
                    Table(adapter)
        table = self.mount(Example())
        grid = table.ui
        self.assertEqual(grid.GetRowLabelSize(), 0)
        self.assertEqual(grid.GetColLabelValue(0), 'Col 0')
        editor = self.editor(grid, 0, 0)
        editor.GetControl().ChangeValue('2.34')
        grid.SaveEditControlValue()
        grid.DisableCellEditControl()
        self.pump()
        self.assertEqual(adapter.values, [[2.3]])
        self.assertEqual(grid.GetCellValue(0, 0), 'Value 2.3')
        editor.DecRef()
        adapter.values = [[3, 4], [5, 6]]
        self.sync()
        self.assertEqual((grid.GetNumberRows(), grid.GetNumberCols()), (2, 2))
        self.assertEqual(grid.GetCellValue(1, 1), 'Value 6')
        adapter.values = []
        self.sync()
        self.assertEqual((grid.GetNumberRows(), grid.GetNumberCols()), (0, 0))

    def test_invalid_counts_and_choices(self):
        for value in (-1, True, 1.5):
            with self.assertRaises(ValueError): Table(rowCount=value)
        for value in ('abc', {1, 2}):
            with self.assertRaises(TypeError): TableNode(choices=value)
