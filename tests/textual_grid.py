import unittest
import PUI.textual as UI


class TextualGrid(unittest.IsolatedAsyncioTestCase):
    async def test_cells_spans_and_breakpoints_keep_the_editor(self):
        class Demo(UI.Application):
            def setup(self):
                self.form = UI.State()
                self.form.text = ''
                self.form.expand = True
            def content(self):
                with UI.Window():
                    with UI.VBox().layout(weight=1):
                        with UI.Grid().columns(1, dense=True, expandChildren=self.form.expand).wideColumns(1, 9).tWideColumns(60, 3) as self.grid:
                            UI.Label('A').grid(columnspan=2).tLayout(height=3)
                            UI.Label('B').grid(columnspan=2, rowspan=2).tLayout(height=6)
                            UI.Label('C').tLayout(height=3)
                            (UI.TextField(self.form('text')).grid(columnspan=1)
                             .wideGrid(1, columnspan=9).tWideGrid(60, columnspan=2).id('editor'))
        root = Demo()
        async with root.ui.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            editor = root.grid.children[-1].ui
            editor.focus()
            await pilot.press(*'typed')
            await pilot.pause()
            self.assertEqual(root.grid._grid_columns, 3)
            self.assertIs(root.grid._grid_dense, True)
            self.assertEqual(root.grid.children[2]._grid_cell, (0, 2, 1, 1))
            self.assertGreater(root.grid.children[1].ui.region.height, root.grid.children[0].ui.region.height)
            for width in (45, 100, 45, 100):
                await pilot.resize_terminal(width, 35)
                await pilot.pause()
                self.assertEqual(root.grid._grid_columns, 3 if width >= 60 else 1)
                self.assertIs(root.grid._grid_dense, True)
                self.assertIs(root.grid.children[-1].ui, editor)
                self.assertEqual(root.grid.children[-1].grid_columnspan, 2 if width >= 60 else 1)
                self.assertEqual(editor.value, 'typed')
                self.assertIs(root.ui.focused, editor)

            for expand in (False, True, False):
                root.form.expand = expand
                await pilot.pause()
                self.assertIs(root.grid.children[-1].ui, editor)
                self.assertEqual(root.grid.children[-1]._grid_cell[3], 3 if expand else 2)
                self.assertEqual(editor.value, 'typed')
                self.assertIs(root.ui.focused, editor)

    async def test_inherited_dense_changes_and_removed_terminal_override(self):
        class Demo(UI.Application):
            def setup(self):
                self.form = UI.State()
                self.form.text = ''
                self.form.override = False
                self.form.dense = True
            def content(self):
                with UI.Window():
                    with UI.Grid() as self.grid:
                        if self.form.override:
                            self.grid.tColumns(2, dense=False, expandChildren=False)
                        self.grid.columns(3, dense=self.form.dense, expandChildren=False)
                        UI.Label('A').grid(columnspan=2)
                        UI.Label('B').grid(columnspan=2)
                        UI.Label('C')
                        UI.TextField(self.form('text')).id('editor')
        root = Demo()
        async with root.ui.run_test(size=(80, 25)) as pilot:
            await pilot.pause()
            editor = root.grid.children[-1].ui
            editor.focus()
            await pilot.press(*'draft')
            for override, dense, columns, cell in (
                    (False, True, 3, (0, 2, 1, 1)),
                    (True, True, 2, (2, 0, 1, 1)),
                    (False, False, 3, (1, 2, 1, 1)),
                    (False, None, 3, (1, 2, 1, 1)),
                    (False, True, 3, (0, 2, 1, 1))):
                root.form.override = override
                root.form.dense = dense
                await pilot.pause()
                self.assertEqual(root.grid._grid_columns, columns)
                self.assertIs(root.grid._grid_dense, False if override else dense)
                self.assertEqual(root.grid.children[2]._grid_cell, cell)
                self.assertIs(root.grid.children[-1].ui, editor)
                self.assertEqual(editor.value, 'draft')
                self.assertIs(root.ui.focused, editor)
