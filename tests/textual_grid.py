import unittest
import PUI.textual as UI


class TextualGrid(unittest.IsolatedAsyncioTestCase):
    async def test_priority_tracks_grow_on_each_axis_and_retain_editors(self):
        class Demo(UI.Application):
            weight = None
            hidden = False
            auto = False
            def content(self):
                with UI.Window():
                    with UI.Grid().tLayout(width=80, height=25) as self.grid:
                        if self.auto:
                            self.grid.columns(3, expandChildren=False)
                        UI.Label('Field').id('label').grid(row=0, column=0).tLayout(weight=self.weight)
                        UI.Label('Value').id('value').grid(row=0, column=1)
                        UI.TextField(UI.DummyBinding('input')).id('input').grid(row=0, column=2).visible(not self.hidden)
                        UI.Label('Body').id('body-label').grid(row=1, column=0, columnspan=2)
                        UI.TextEdit(UI.DummyBinding('body')).id('body').grid(row=1, column=2).visible(not self.hidden)
                        UI.Label('Footer').id('footer').grid(row=2, column=0, columnspan=3)
        root = Demo()
        async with root.ui.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            def item(name):
                return next(child.ui for child in root.grid.children if child._id == name)
            editor = item('input')
            initial = item('label').region.size
            self.assertEqual(initial.width, 5)
            self.assertGreater(editor.region.width, 60)
            self.assertLess(editor.region.height, 5)
            self.assertGreater(item('body').region.height, 15)
            root.auto = True
            root.sync()
            await pilot.pause()
            self.assertEqual(item('label').region.size, initial)
            root.auto, root.weight = False, 2
            root.sync()
            await pilot.pause()
            self.assertGreater(item('label').region.width, 50)
            self.assertGreater(item('label').region.height, 15)
            root.weight = 0
            root.sync()
            await pilot.pause()
            self.assertEqual(item('label').region.size, initial)
            self.assertIs(item('input'), editor)
            root.hidden = True
            root.sync()
            await pilot.pause()
            self.assertLess(item('footer').region.width, 20)
            self.assertEqual(item('footer').region.height, 1)

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
