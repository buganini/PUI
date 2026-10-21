"""Responsive grid placement must retain declaration identity and controls."""
import asyncio
import unittest
from PUI.web import Application, Window, Grid, TextField, Label, State
from PUI.web.runtime import Runtime


class WideGridTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, automatic, terminal=False):
        class Demo(Application):
            def setup(self):
                self.form = State()
                self.form.text = 'retained draft'
            def content(self):
                with Window():
                    with Grid() as grid:
                        if automatic:
                            grid.columns(3, dense=True)
                        field = TextField(self.form('text')).grid(row=0, column=0)
                        field._terminal_units = terminal
                        (field.wideGrid(600, row=1, column=1, columnspan=2)
                         .wideGrid(800, rowspan=2).wideGrid(600, column=0)
                         .tWideGrid(60, row=1, column=0, columnspan=2)
                         .tWideGrid(80, rowspan=2).id('editor').ref('wide_grid.editor'))
                        Label('other').grid(row=0, column=2).id('other')
        runtime = Runtime(asyncio.get_running_loop())
        runtime.app = Demo()
        try:
            runtime.app.sync()
            runtime.snapshot()
            grid = runtime.app.children[0].children[0]
            field = grid.children[0]
            key, native = field.key, field.ui
            token = native.attachments['model']['token']
            for width in ((59, 60, 80, 40, 60) if terminal else (599, 600, 800, 400, 600)):
                grid.get_node()._set_size(width, 400)
                runtime.flush()
                runtime.snapshot()
                current = grid.get_node()
                field = next(n for n in current.children if n._id == 'editor')
                wide = width >= (60 if terminal else 600)
                tall = width >= (80 if terminal else 800)
                self.assertEqual(field.key, key)
                self.assertIs(field.ui, native)
                self.assertEqual(native.attachments['model']['token'], token)
                self.assertEqual(runtime.app.form.text, 'retained draft')
                self.assertEqual(field.grid_columnspan, 2 if wide else None)
                self.assertEqual(field.grid_rowspan, 2 if tall else None)
                cell = next(cell for node, cell in current.grid_cells(current.children) if node is field)
                self.assertEqual(cell, (0 if automatic else int(wide), 0,
                                        2 if tall else 1, 2 if wide else 1))
        finally:
            runtime.close()

    async def test_manual(self):
        await self.exercise(False)

    async def test_automatic_dense(self):
        await self.exercise(True)

    async def test_terminal_units(self):
        await self.exercise(True, True)
