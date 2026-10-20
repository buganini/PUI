import unittest
import PUI.textual as UI


class TextualGrid(unittest.IsolatedAsyncioTestCase):
    async def test_cells_spans_and_breakpoints_keep_the_editor(self):
        class Demo(UI.Application):
            def setup(self):
                self.form = UI.State()
                self.form.text = ''
            def content(self):
                with UI.Window():
                    with UI.VBox().layout(weight=1):
                        with UI.Grid().tColumns(1, dense=True).tWideColumns(60, 3) as self.grid:
                            UI.Label('A').grid(columnspan=2).tLayout(height=3)
                            UI.Label('B').grid(columnspan=2, rowspan=2).tLayout(height=6)
                            UI.Label('C').tLayout(height=3)
                            UI.TextField(self.form('text')).id('editor')
        root = Demo()
        async with root.ui.run_test(size=(100, 35)) as pilot:
            await pilot.pause()
            editor = root.grid.children[-1].ui
            editor.focus()
            await pilot.press(*'typed')
            await pilot.pause()
            self.assertEqual(root.grid._grid_columns, 3)
            self.assertEqual(root.grid.children[2]._grid_cell, (0, 2, 1, 1))
            self.assertGreater(root.grid.children[1].ui.region.height, root.grid.children[0].ui.region.height)
            for width in (45, 100, 45, 100):
                await pilot.resize_terminal(width, 35)
                await pilot.pause()
                self.assertEqual(root.grid._grid_columns, 3 if width >= 60 else 1)
                self.assertIs(root.grid.children[-1].ui, editor)
                self.assertEqual(editor.value, 'typed')
                self.assertIs(root.ui.focused, editor)
